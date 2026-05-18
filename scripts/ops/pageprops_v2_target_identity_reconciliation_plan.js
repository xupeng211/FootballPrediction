#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const {
    CANDIDATE_VERSION,
    HASH_STRATEGY,
    buildFotMobMatchUrl,
    fetchHtml,
    extractNextDataJsonFromHtml,
    getPageProps,
    computeStablePagePropsHash,
    listJsonPaths,
} = require('./pageprops_v2_no_write_preview');

const PHASE = 'PHASE5_21L2V3D_TARGET_IDENTITY_RECONCILIATION_PLANNING';
const MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const RENEWED_PROPOSAL_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.renewed_baseline_proposal.phase521l2v3c.json';
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3D.md';
const SOURCE = 'fotmob';
const ROUTE = 'html_hydration';
const LEAGUE_ID = 53;
const LEAGUE_NAME = 'Ligue 1';
const SEASON = '2025/2026';
const RAW_VERSION = CANDIDATE_VERSION;
const BATCH_ID = 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001';
const TARGET_COUNT = 50;
const KNOWN_COMPLETED_COUNT = 8;
const EXPECTED_MISMATCH_COUNT = 8;
const DEFAULT_REQUEST_DELAY_MS = 750;
const REQUIRED_YES_FLAGS = Object.freeze([
    'planningAuthorization',
    'targetIdentityReconciliationAuthorization',
    'networkAuthorization',
    'matchDetailRecaptureAuthorization',
]);
const REQUIRED_NO_FLAGS = Object.freeze([
    'allowDbWrite',
    'allowRawMatchDataWrite',
    'allowControlledWrite',
    'allowMatchesWrite',
    'allowBookmakerOddsWrite',
    'allowFeatureWrite',
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
    'allowOddsWrite',
    'executeWrite',
    'commit',
    'finalDbWriteConfirmation',
    'acceptBaseline',
    'acceptedBaseline',
    'baselineAcceptanceAuthorization',
    'rawWriteReadyForExecution',
    'rawWriteRetryAuthorization',
]);
const EXPECTED_ROW_COUNTS = Object.freeze({
    matches: 60,
    raw_match_data: 18,
    bookmaker_odds_history: 2,
    l3_features: 2,
    match_features_training: 2,
    predictions: 2,
});
const ALLOWED_MANIFEST_NEXT_STEPS = Object.freeze([
    'target_identity_reconciliation_planning',
    'target_identity_source_inventory_reconciliation_planning',
    'target_identity_reconciliation_follow_up_investigation',
    'route_generation_fix_planning',
    'renewed_baseline_acceptance_review_planning',
]);

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
        renewedProposal: RENEWED_PROPOSAL_PATH,
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
        planningAuthorization: null,
        targetIdentityReconciliationAuthorization: null,
        networkAuthorization: null,
        matchDetailRecaptureAuthorization: null,
        allowDbWrite: null,
        allowRawMatchDataWrite: null,
        allowControlledWrite: null,
        allowMatchesWrite: null,
        allowBookmakerOddsWrite: null,
        allowFeatureWrite: null,
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
        allowOddsWrite: false,
        executeWrite: false,
        commit: false,
        finalDbWriteConfirmation: false,
        acceptBaseline: false,
        acceptedBaseline: false,
        baselineAcceptanceAuthorization: false,
        rawWriteReadyForExecution: false,
        rawWriteRetryAuthorization: false,
        retry: 0,
        requestDelayMs: DEFAULT_REQUEST_DELAY_MS,
        targetExternalIds: null,
        generatedAt: null,
        baseHead: null,
        branch: null,
        mainHead: null,
        mainCiStatus: null,
        pr1276MergeCommit: null,
        pr1276State: null,
        pr1277MergeCommit: null,
        pr1277State: null,
        pr1277RetargetResult: null,
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

function normalizePlanningInput(input = {}) {
    return {
        manifest: normalizeText(input.manifest),
        renewedProposal: normalizeText(input.renewedProposal) || RENEWED_PROPOSAL_PATH,
        reportOutput: normalizeText(input.reportOutput) || REPORT_PATH,
        source: normalizeLower(input.source),
        leagueId: parseInteger(input.leagueId, null),
        leagueName: normalizeText(input.leagueName),
        season: normalizeText(input.season),
        route: normalizeText(input.route),
        rawVersion: normalizeText(input.rawVersion),
        hashStrategy: normalizeText(input.hashStrategy),
        batchId: normalizeText(input.batchId),
        targetCount: parseInteger(input.targetCount, null),
        planningAuthorization: normalizeBooleanFlag(input.planningAuthorization, undefined),
        targetIdentityReconciliationAuthorization: normalizeBooleanFlag(
            input.targetIdentityReconciliationAuthorization,
            undefined
        ),
        networkAuthorization: normalizeBooleanFlag(input.networkAuthorization, undefined),
        matchDetailRecaptureAuthorization: normalizeBooleanFlag(input.matchDetailRecaptureAuthorization, undefined),
        allowDbWrite: normalizeBooleanFlag(input.allowDbWrite, undefined),
        allowRawMatchDataWrite: normalizeBooleanFlag(input.allowRawMatchDataWrite, undefined),
        allowControlledWrite: normalizeBooleanFlag(input.allowControlledWrite, undefined),
        allowMatchesWrite: normalizeBooleanFlag(input.allowMatchesWrite, undefined),
        allowBookmakerOddsWrite: normalizeBooleanFlag(input.allowBookmakerOddsWrite, undefined),
        allowFeatureWrite: normalizeBooleanFlag(input.allowFeatureWrite, undefined),
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
        allowOddsWrite: normalizeBooleanFlag(input.allowOddsWrite, false),
        executeWrite: normalizeBooleanFlag(input.executeWrite, false),
        commit: normalizeBooleanFlag(input.commit, false),
        finalDbWriteConfirmation: normalizeBooleanFlag(input.finalDbWriteConfirmation, false),
        acceptBaseline: normalizeBooleanFlag(input.acceptBaseline, false),
        acceptedBaseline: normalizeBooleanFlag(input.acceptedBaseline, false),
        baselineAcceptanceAuthorization: normalizeBooleanFlag(input.baselineAcceptanceAuthorization, false),
        rawWriteReadyForExecution: normalizeBooleanFlag(input.rawWriteReadyForExecution, false),
        rawWriteRetryAuthorization: normalizeBooleanFlag(input.rawWriteRetryAuthorization, false),
        retry: parseInteger(input.retry, 0),
        requestDelayMs: parseInteger(input.requestDelayMs, DEFAULT_REQUEST_DELAY_MS),
        targetExternalIds: Array.isArray(input.targetExternalIds)
            ? input.targetExternalIds.map(normalizeText).filter(Boolean)
            : parseCsv(input.targetExternalIds),
        generatedAt: normalizeText(input.generatedAt),
        baseHead: normalizeText(input.baseHead),
        branch: normalizeText(input.branch),
        mainHead: normalizeText(input.mainHead),
        mainCiStatus: normalizeText(input.mainCiStatus),
        pr1276MergeCommit: normalizeText(input.pr1276MergeCommit),
        pr1276State: normalizeText(input.pr1276State),
        pr1277MergeCommit: normalizeText(input.pr1277MergeCommit),
        pr1277State: normalizeText(input.pr1277State),
        pr1277RetargetResult: normalizeText(input.pr1277RetargetResult),
        unknown: Array.isArray(input.unknown) ? input.unknown : [],
    };
}

function pushRequiredYes(errors, value, name) {
    if (value === true) return;
    errors.push(value === false ? `${name}=yes is required in Phase 5.21L2V3D` : `missing ${name}=yes`);
}

function pushRequiredNo(errors, value, name) {
    if (value === false) return;
    errors.push(value === true ? `${name}=yes is blocked in Phase 5.21L2V3D` : `missing ${name}=no`);
}

function requireExact(errors, actual, expected, name) {
    if (!normalizeText(actual)) {
        errors.push(`missing ${name}=${expected}`);
        return;
    }
    if (normalizeText(actual) !== expected) errors.push(`${name} must be ${expected}`);
}

function validatePlanningInput(rawInput = {}) {
    const input = normalizePlanningInput(rawInput);
    const errors = [];
    if (input.unknown.length > 0) errors.push(`unknown arguments: ${input.unknown.join(',')}`);
    requireExact(errors, input.manifest, MANIFEST_PATH, 'manifest');
    requireExact(errors, input.renewedProposal, RENEWED_PROPOSAL_PATH, 'renewed-proposal');
    requireExact(errors, input.reportOutput, REPORT_PATH, 'report-output');
    requireExact(errors, input.source, SOURCE, 'source');
    if (input.leagueId !== LEAGUE_ID) errors.push(`league-id must be ${LEAGUE_ID}`);
    requireExact(errors, input.leagueName, LEAGUE_NAME, 'league-name');
    requireExact(errors, input.season, SEASON, 'season');
    requireExact(errors, input.route, ROUTE, 'route');
    requireExact(errors, input.rawVersion, RAW_VERSION, 'raw-version');
    requireExact(errors, input.hashStrategy, HASH_STRATEGY, 'hash-strategy');
    requireExact(errors, input.batchId, BATCH_ID, 'batch-id');
    if (input.targetCount !== TARGET_COUNT) errors.push(`target-count must be ${TARGET_COUNT}`);
    for (const key of REQUIRED_YES_FLAGS) pushRequiredYes(errors, input[key], flagName(key));
    for (const key of REQUIRED_NO_FLAGS) pushRequiredNo(errors, input[key], flagName(key));
    for (const key of BLOCKED_TRUE_FLAGS) {
        if (input[key] === true) errors.push(`${flagName(key)}=yes is blocked in Phase 5.21L2V3D`);
    }
    if (input.retry !== 0) errors.push('retry must be 0');
    if (!Number.isInteger(input.requestDelayMs) || input.requestDelayMs < 0) {
        errors.push('request-delay-ms must be a non-negative integer');
    }
    return { ok: errors.length === 0, input, errors };
}

function readJsonFile(filePath) {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function writeJsonFile(filePath, data) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, `${JSON.stringify(data, null, 4)}\n`);
}

function writeReportFile(filePath, content) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, content);
}

function isPlainObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function normalizeCandidateTarget(target = {}) {
    return {
        ...target,
        match_id: normalizeText(target.match_id),
        external_id: normalizeText(target.external_id),
        home_team: normalizeText(target.home_team),
        away_team: normalizeText(target.away_team),
        kickoff_time: normalizeText(target.kickoff_time || target.match_date),
        match_date: normalizeText(target.match_date || target.kickoff_time),
        status: normalizeLower(target.status),
        baseline_hash: normalizeLower(target.baseline_hash),
        preflight_status: normalizeText(target.preflight_status),
        matches_seed_status: normalizeText(target.matches_seed_status),
        source_url: target.source_url || null,
    };
}

function validateManifestGate(manifest = {}) {
    const errors = [];
    const candidates = Array.isArray(manifest.candidate_targets)
        ? manifest.candidate_targets.map(normalizeCandidateTarget)
        : [];
    if (normalizeText(manifest.batch_id) !== BATCH_ID) errors.push('manifest batch_id mismatch');
    if (normalizeLower(manifest.source) !== SOURCE) errors.push('manifest source mismatch');
    if (normalizeText(manifest.route) !== ROUTE) errors.push('manifest route mismatch');
    if (normalizeText(manifest.raw_data_version) !== RAW_VERSION) errors.push('manifest raw_data_version mismatch');
    if (normalizeText(manifest.hash_strategy) !== HASH_STRATEGY) errors.push('manifest hash_strategy mismatch');
    if (candidates.length !== TARGET_COUNT) errors.push(`candidate_targets must contain ${TARGET_COUNT} targets`);
    if (
        !Array.isArray(manifest.known_completed_targets) ||
        manifest.known_completed_targets.length !== KNOWN_COMPLETED_COUNT
    ) {
        errors.push(`known_completed_targets must contain ${KNOWN_COMPLETED_COUNT} targets`);
    }
    if (normalizeText(manifest.phase_5_21_l2v3c_planning_status) !== 'completed_no_write') {
        errors.push('phase_5_21_l2v3c_planning_status must be completed_no_write');
    }
    if (Number(manifest.phase_5_21_l2v3c_metadata_target_mismatch_count || 0) !== EXPECTED_MISMATCH_COUNT) {
        errors.push(`phase_5_21_l2v3c_metadata_target_mismatch_count must be ${EXPECTED_MISMATCH_COUNT}`);
    }
    if (!ALLOWED_MANIFEST_NEXT_STEPS.includes(normalizeText(manifest.next_required_step))) {
        errors.push('next_required_step must be target identity reconciliation planning or a prior L2V3D outcome');
    }
    if (manifest.renewed_baseline_requires_separate_baseline_acceptance !== true) {
        errors.push('renewed_baseline_requires_separate_baseline_acceptance must be true');
    }
    if (manifest.renewed_baseline_requires_separate_final_db_write_authorization !== true) {
        errors.push('renewed_baseline_requires_separate_final_db_write_authorization must be true');
    }
    if (manifest.raw_write_ready_for_execution === true) {
        errors.push('raw_write_ready_for_execution must not be true');
    }
    for (const target of candidates) {
        const expectedMatchId = `${LEAGUE_ID}_20252026_${target.external_id}`;
        if (!/^\d+$/.test(target.external_id)) errors.push(`external_id must be numeric for ${target.match_id}`);
        if (target.match_id !== expectedMatchId) errors.push(`match_id convention mismatch for ${target.external_id}`);
        if (!/^[a-f0-9]{64}$/.test(target.baseline_hash)) {
            errors.push(`baseline_hash invalid for ${target.external_id}`);
        }
        if (target.preflight_status !== 'hash_baseline_ready') {
            errors.push(`preflight_status must be hash_baseline_ready for ${target.external_id}`);
        }
        if (target.matches_seed_status !== 'inserted_matches_identity') {
            errors.push(`matches_seed_status must be inserted_matches_identity for ${target.external_id}`);
        }
    }
    return {
        ok: errors.length === 0,
        errors,
        candidates,
        candidate_targets_count: candidates.length,
        known_completed_targets_count: Array.isArray(manifest.known_completed_targets)
            ? manifest.known_completed_targets.length
            : 0,
    };
}

function validateRenewedProposalGate(proposal = {}) {
    const errors = [];
    const checkedTargets = Array.isArray(proposal.checked_targets) ? proposal.checked_targets : [];
    if (proposal.proposal_phase !== 'Phase 5.21L2V3C') errors.push('proposal_phase must be Phase 5.21L2V3C');
    if (proposal.no_write !== true) errors.push('proposal no_write must be true');
    if (proposal.db_write_performed !== false) errors.push('proposal db_write_performed must be false');
    if (proposal.raw_insert_performed !== false) errors.push('proposal raw_insert_performed must be false');
    if (Number(proposal.summary?.metadata_target_mismatch_count || 0) !== EXPECTED_MISMATCH_COUNT) {
        errors.push(`proposal metadata_target_mismatch_count must be ${EXPECTED_MISMATCH_COUNT}`);
    }
    if (proposal.summary?.next_required_step !== 'target_identity_reconciliation_planning') {
        errors.push('proposal next_required_step must be target_identity_reconciliation_planning');
    }
    if (proposal.recommendation?.raw_write_ready_for_execution !== false) {
        errors.push('proposal raw_write_ready_for_execution must be false');
    }
    if (proposal.recommendation?.requires_separate_baseline_acceptance !== true) {
        errors.push('proposal requires_separate_baseline_acceptance must be true');
    }
    if (proposal.recommendation?.requires_separate_final_db_write_authorization !== true) {
        errors.push('proposal requires_separate_final_db_write_authorization must be true');
    }
    if (checkedTargets.length !== EXPECTED_MISMATCH_COUNT) {
        errors.push(`proposal checked_targets must contain ${EXPECTED_MISMATCH_COUNT} targets`);
    }
    for (const target of checkedTargets) {
        if (target.hash_status !== 'metadata_target_mismatch') {
            errors.push(`proposal target ${target.external_id} must be metadata_target_mismatch`);
        }
        if (target.metadata_identity_status !== 'metadata_target_mismatch') {
            errors.push(`proposal target ${target.external_id} metadata_identity_status must be mismatch`);
        }
    }
    return { ok: errors.length === 0, errors, checkedTargets };
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

function externalIdFromUrl(rawUrl) {
    const value = normalizeText(rawUrl);
    if (!value) return null;
    try {
        const url = new URL(value);
        const hashMatch = url.hash.match(/(\d{6,})/);
        if (hashMatch) return hashMatch[1];
        const pathMatch = url.pathname.match(/\/match\/(?:[^/]+\/)*(\d{6,})(?:\/)?$/);
        if (pathMatch) return pathMatch[1];
        const searchMatch = url.search.match(/(?:matchId|id)=(\d{6,})/i);
        return searchMatch?.[1] || null;
    } catch (_error) {
        const match = value.match(/\/match\/(?:[^/]+\/)*(\d{6,})(?:[/?#]|$)/);
        return match?.[1] || null;
    }
}

function normalizeComparableDate(value) {
    const text = normalizeText(value);
    if (!text) return '';
    const date = new Date(text);
    if (Number.isNaN(date.getTime())) return text;
    return date.toISOString();
}

function teamsMatch(requested = {}, observed = {}) {
    const requestedHome = normalizeLower(requested.home_team);
    const requestedAway = normalizeLower(requested.away_team);
    const observedHome = normalizeLower(observed.home_team);
    const observedAway = normalizeLower(observed.away_team);
    return Boolean(requestedHome && requestedAway && requestedHome === observedHome && requestedAway === observedAway);
}

function datesMatch(requested = {}, observed = {}) {
    const requestedDate = normalizeComparableDate(requested.kickoff_time || requested.match_date);
    const observedDate = normalizeComparableDate(observed.match_time_utc);
    return Boolean(requestedDate && observedDate && requestedDate === observedDate);
}

function extractSafeIdentityFromPageProps(pageProps = {}) {
    if (!isPlainObject(pageProps)) {
        return {
            external_id: null,
            match_identifier_fields: {},
            home_team: null,
            away_team: null,
            match_name: null,
            match_time_utc: null,
            status: null,
            league_id: null,
        };
    }
    const general = isPlainObject(pageProps.general) ? pageProps.general : {};
    const header = isPlainObject(pageProps.header) ? pageProps.header : {};
    const teams = Array.isArray(header.teams) ? header.teams : [];
    const externalId = normalizeText(general.matchId || general.matchID || general.id || pageProps.matchId);
    return {
        external_id: externalId || null,
        match_identifier_fields: {
            general_matchId: normalizeText(general.matchId) || null,
            general_matchID: normalizeText(general.matchID) || null,
            general_id: normalizeText(general.id) || null,
            top_level_matchId: normalizeText(pageProps.matchId) || null,
        },
        home_team: normalizeText(teams[0]?.name || header.homeTeam?.name || header.homeTeam) || null,
        away_team: normalizeText(teams[1]?.name || header.awayTeam?.name || header.awayTeam) || null,
        match_name: normalizeText(general.matchName) || null,
        match_time_utc: normalizeText(general.matchTimeUTCDate || general.matchTimeUTC) || null,
        status: normalizeText(general.matchStatus || general.status || header.status) || null,
        league_id: normalizeText(general.leagueId || general.parentLeagueId) || null,
    };
}

function observedExternalIdSuffix(identity = {}) {
    const observed = normalizeText(identity.external_id);
    return observed.match(/(\d+)$/)?.[1] || observed || null;
}

function classifyDiagnostic(diagnostic = {}) {
    const reasons = [];
    if (diagnostic.request_url_external_id && diagnostic.request_url_external_id !== diagnostic.requested_external_id) {
        return {
            mismatch_type: 'route_generation_mismatch',
            reasons: ['request URL id differs from target external_id'],
        };
    }
    if (diagnostic.final_url_external_id && diagnostic.final_url_external_id !== diagnostic.requested_external_id) {
        reasons.push('final URL id differs from target external_id');
        return { mismatch_type: 'canonical_redirect_mismatch', reasons };
    }
    if (!diagnostic.parsed) {
        return { mismatch_type: 'unknown', reasons: ['pageProps was not parsed'] };
    }
    if (diagnostic.observed_external_id && diagnostic.observed_external_id !== diagnostic.requested_external_id) {
        reasons.push('pageProps identity external_id differs from requested external_id');
        if (!diagnostic.team_match || !diagnostic.date_match) {
            reasons.push('observed team/date metadata differs from manifest target metadata');
        }
        return { mismatch_type: 'requested_vs_observed_external_id_mismatch', reasons };
    }
    if (!diagnostic.team_match || !diagnostic.date_match) {
        return {
            mismatch_type: 'team_date_status_mismatch',
            reasons: ['external_id matched but team/date metadata differed'],
        };
    }
    return { mismatch_type: 'identity_match', reasons: [] };
}

function summarizeTopLevelKeys(pageProps = {}) {
    return isPlainObject(pageProps) ? Object.keys(pageProps).sort() : [];
}

function jsonByteLength(value = {}) {
    return Buffer.byteLength(JSON.stringify(value), 'utf8');
}

async function sleep(ms) {
    if (!ms) return;
    await new Promise(resolve => {
        setTimeout(resolve, ms);
    });
}

async function resolveFetchResult(target = {}, requestUrl, index, dependencies = {}) {
    const byExternalId = dependencies.fetchResultsByExternalId || {};
    if (byExternalId[target.external_id]) return byExternalId[target.external_id];
    if (Array.isArray(dependencies.fetchResults) && dependencies.fetchResults[index]) {
        return dependencies.fetchResults[index];
    }
    const fetchHtmlFn = dependencies.fetchHtmlFn || fetchHtml;
    return fetchHtmlFn(requestUrl, { fetchFn: dependencies.fetchFn });
}

async function diagnoseTarget(target = {}, proposalTarget = {}, index = 0, input = {}, dependencies = {}) {
    if (index > 0) await sleep(input.requestDelayMs);
    const requestedExternalId = normalizeText(target.external_id);
    const builtRequestUrl = buildFotMobMatchUrl(requestedExternalId);
    const fetchResult = await resolveFetchResult(target, builtRequestUrl, index, dependencies);
    const requestUrl = fetchResult.request_url || builtRequestUrl;
    const finalUrl = fetchResult.final_url || requestUrl;
    const base = {
        requested_external_id: requestedExternalId,
        requested_match_id: target.match_id,
        requested_home_team: target.home_team || null,
        requested_away_team: target.away_team || null,
        requested_kickoff_time: target.kickoff_time || target.match_date || null,
        requested_status: target.status || null,
        request_url_summary: safeUrlSummary(requestUrl),
        request_url_external_id: externalIdFromUrl(requestUrl),
        final_url_summary: safeUrlSummary(finalUrl),
        final_url_external_id: externalIdFromUrl(finalUrl),
        http_status: Number(fetchResult.http_status || fetchResult.status || 0),
        parsed: false,
        observed_external_id: null,
        observed_match_identifier_fields: {},
        observed_home_team: null,
        observed_away_team: null,
        observed_match_name: null,
        observed_match_time_utc: null,
        observed_status: null,
        observed_league_id: null,
        top_level_keys_summary: [],
        body_byte_length: Number(fetchResult.body_byte_length || 0),
        pageprops_json_byte_length: null,
        pageProps_path_count: null,
        pageProps_content_path_count: null,
        hash: null,
        l2v3c_previous_hash: proposalTarget.renewed_candidate_hash || null,
        l2v3c_previous_observed_external_id:
            proposalTarget.attempts?.[0]?.metadata_identity_observed?.external_id || null,
        identity_match: false,
        team_match: false,
        date_match: false,
        mismatch_type: 'unknown',
        mismatch_type_reasons: [],
        deterministic_observed_identity_with_l2v3c: false,
        deterministic_with_l2v3c: false,
        safe_error_summary: fetchResult.error || null,
    };
    if (!fetchResult.ok || Number(fetchResult.http_status || 0) !== 200) {
        return { ...base, safe_error_summary: fetchResult.error || 'HTTP_NON_200' };
    }
    const extraction = extractNextDataJsonFromHtml(fetchResult.body);
    if (!extraction.ok) {
        return { ...base, safe_error_summary: extraction.error || 'NEXT_DATA_PARSE_FAILED' };
    }
    const pageProps = getPageProps(extraction.data);
    if (!pageProps) {
        return { ...base, safe_error_summary: 'PAGE_PROPS_NOT_FOUND' };
    }
    const identity = extractSafeIdentityFromPageProps(pageProps);
    const observedId = observedExternalIdSuffix(identity);
    const pagePropsPaths = listJsonPaths(pageProps);
    const contentPaths = listJsonPaths(isPlainObject(pageProps.content) ? pageProps.content : {});
    const hash = computeStablePagePropsHash(pageProps);
    const parsed = {
        ...base,
        parsed: true,
        observed_external_id: observedId,
        observed_match_identifier_fields: identity.match_identifier_fields,
        observed_home_team: identity.home_team,
        observed_away_team: identity.away_team,
        observed_match_name: identity.match_name,
        observed_match_time_utc: identity.match_time_utc,
        observed_status: identity.status,
        observed_league_id: identity.league_id,
        top_level_keys_summary: summarizeTopLevelKeys(pageProps),
        pageprops_json_byte_length: jsonByteLength(pageProps),
        pageProps_path_count: pagePropsPaths.length,
        pageProps_content_path_count: contentPaths.length,
        hash,
        identity_match: Boolean(observedId && observedId === requestedExternalId),
        team_match: teamsMatch(target, identity),
        date_match: datesMatch(target, identity),
        deterministic_with_l2v3c:
            Boolean(proposalTarget.renewed_candidate_hash && proposalTarget.renewed_candidate_hash === hash) &&
            Boolean(proposalTarget.attempts?.[0]?.metadata_identity_observed?.external_id === observedId),
        deterministic_observed_identity_with_l2v3c:
            Boolean(proposalTarget.attempts?.[0]?.metadata_identity_observed?.external_id) &&
            proposalTarget.attempts?.[0]?.metadata_identity_observed?.external_id === observedId,
        safe_error_summary: null,
    };
    const classification = classifyDiagnostic(parsed);
    return {
        ...parsed,
        mismatch_type: classification.mismatch_type,
        mismatch_type_reasons: classification.reasons,
    };
}

function selectMismatchTargets(manifestGate = {}, proposalGate = {}, requestedExternalIds = []) {
    const candidatesByExternalId = new Map(
        (manifestGate.candidates || []).map(target => [normalizeText(target.external_id), target])
    );
    const proposalByExternalId = new Map(
        (proposalGate.checkedTargets || []).map(target => [normalizeText(target.external_id), target])
    );
    const selectedIds =
        requestedExternalIds.length > 0
            ? requestedExternalIds
            : (proposalGate.checkedTargets || []).map(target => normalizeText(target.external_id));
    const uniqueIds = [...new Set(selectedIds.map(normalizeText).filter(Boolean))];
    const errors = [];
    const pairs = [];
    for (const externalId of uniqueIds) {
        const target = candidatesByExternalId.get(externalId);
        const proposalTarget = proposalByExternalId.get(externalId);
        if (!target) errors.push(`target ${externalId} missing from manifest candidate_targets`);
        if (!proposalTarget) errors.push(`target ${externalId} missing from L2V3C mismatch proposal`);
        if (target && proposalTarget) pairs.push({ target, proposalTarget });
    }
    return { ok: errors.length === 0, errors, pairs, selected_external_ids: uniqueIds };
}

function countBy(values = []) {
    return values.reduce((acc, value) => {
        const key = normalizeText(value) || 'unknown';
        acc[key] = (acc[key] || 0) + 1;
        return acc;
    }, {});
}

function inferRootCause(summary = {}, diagnostics = []) {
    if (summary.identity_mismatch_count === 0) {
        return {
            root_cause_status: 'not_applicable',
            suspected_root_cause: 'identity_reconciled',
            next_required_step: 'renewed_baseline_acceptance_review_planning',
        };
    }
    if (summary.request_url_itself_wrong === true) {
        return {
            root_cause_status: 'confirmed_route_generation_mismatch',
            suspected_root_cause: 'route_generation_mismatch',
            next_required_step: 'route_generation_fix_planning',
        };
    }
    if (summary.canonical_redirect_detected === true) {
        return {
            root_cause_status: 'suspected_not_accepted',
            suspected_root_cause: 'fotmob_canonical_redirect_or_detail_route_identity_mismatch',
            next_required_step: 'target_identity_source_inventory_reconciliation_planning',
        };
    }
    const allObservedMismatch = diagnostics.every(
        item => item.mismatch_type === 'requested_vs_observed_external_id_mismatch'
    );
    if (allObservedMismatch) {
        return {
            root_cause_status: 'suspected_not_accepted',
            suspected_root_cause: 'manifest_target_identity_or_fotmob_detail_payload_mapping_mismatch',
            next_required_step: 'target_identity_source_inventory_reconciliation_planning',
        };
    }
    return {
        root_cause_status: 'unknown',
        suspected_root_cause: 'unknown',
        next_required_step: 'target_identity_reconciliation_follow_up_investigation',
    };
}

function buildSummary({ diagnostics = [], input = {}, manifestGate = {}, proposalGate = {}, generatedAt } = {}) {
    const mismatchTypeCounts = countBy(diagnostics.map(item => item.mismatch_type));
    const identityMatchCount = diagnostics.filter(item => item.identity_match === true).length;
    const identityMismatchCount = diagnostics.length - identityMatchCount;
    const deterministicCount = diagnostics.filter(item => item.deterministic_with_l2v3c === true).length;
    const deterministicIdentityCount = diagnostics.filter(
        item => item.deterministic_observed_identity_with_l2v3c === true
    ).length;
    const requestUrlItselfWrong = diagnostics.some(item => item.mismatch_type === 'route_generation_mismatch');
    const canonicalRedirectDetected = diagnostics.some(item => item.mismatch_type === 'canonical_redirect_mismatch');
    const parserExtractorWrongIndicated = diagnostics.some(
        item => item.mismatch_type === 'pageprops_extraction_wrong_node'
    );
    const manifestTargetMetadataMismatchIndicated = diagnostics.some(
        item =>
            item.mismatch_type === 'requested_vs_observed_external_id_mismatch' &&
            (!item.team_match || !item.date_match)
    );
    const baseSummary = {
        phase: PHASE,
        generated_at: generatedAt,
        branch: input.branch || null,
        base_head: input.baseHead || null,
        main_head: input.mainHead || null,
        main_ci_status: input.mainCiStatus || null,
        pr_1276_state: input.pr1276State || null,
        pr_1276_merge_commit: input.pr1276MergeCommit || null,
        pr_1277_state: input.pr1277State || null,
        pr_1277_merge_commit: input.pr1277MergeCommit || null,
        pr_1277_retarget_result: input.pr1277RetargetResult || null,
        source_manifest_path: input.manifest,
        renewed_baseline_proposal_path: input.renewedProposal,
        report_path: input.reportOutput,
        no_write: true,
        db_write_performed: false,
        raw_insert_performed: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        candidate_targets_count: manifestGate.candidate_targets_count,
        l2v3c_metadata_target_mismatch_count: proposalGate.checkedTargets?.length || 0,
        checked_target_count: diagnostics.length,
        identity_match_count: identityMatchCount,
        identity_mismatch_count: identityMismatchCount,
        mismatch_type_counts: mismatchTypeCounts,
        deterministic_observed_identity_with_l2v3c_count: deterministicIdentityCount,
        deterministic_observed_identity_with_l2v3c:
            diagnostics.length > 0 && deterministicIdentityCount === diagnostics.length,
        deterministic_with_l2v3c_count: deterministicCount,
        deterministic_with_l2v3c: diagnostics.length > 0 && deterministicCount === diagnostics.length,
        all_mismatches_same_pattern: Object.keys(mismatchTypeCounts).length === 1,
        request_url_itself_wrong: requestUrlItselfWrong,
        canonical_redirect_detected: canonicalRedirectDetected,
        response_canonical_data_wrong_or_unexpected: identityMismatchCount > 0,
        parser_extractor_wrong_indicated: parserExtractorWrongIndicated,
        manifest_target_metadata_mismatch_indicated: manifestTargetMetadataMismatchIndicated,
        raw_write_ready_for_execution: false,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
    };
    return { ...baseSummary, ...inferRootCause(baseSummary, diagnostics) };
}

function buildUpdatedManifest(manifest = {}, summary = {}) {
    return {
        ...manifest,
        phase_5_21_l2v3d_planning_status: 'completed_no_write',
        target_identity_reconciliation_status:
            summary.identity_mismatch_count > 0
                ? 'blocked_identity_mismatch_unresolved'
                : 'identity_reconciled_no_write',
        phase_5_21_l2v3d_checked_target_count: summary.checked_target_count,
        phase_5_21_l2v3d_identity_match_count: summary.identity_match_count,
        phase_5_21_l2v3d_identity_mismatch_count: summary.identity_mismatch_count,
        phase_5_21_l2v3d_mismatch_type_counts: summary.mismatch_type_counts,
        phase_5_21_l2v3d_deterministic_observed_identity_with_l2v3c: summary.deterministic_observed_identity_with_l2v3c,
        phase_5_21_l2v3d_deterministic_with_l2v3c: summary.deterministic_with_l2v3c,
        phase_5_21_l2v3d_request_url_itself_wrong: summary.request_url_itself_wrong,
        phase_5_21_l2v3d_parser_extractor_wrong_indicated: summary.parser_extractor_wrong_indicated,
        phase_5_21_l2v3d_manifest_target_metadata_mismatch_indicated:
            summary.manifest_target_metadata_mismatch_indicated,
        phase_5_21_l2v3d_root_cause_status: summary.root_cause_status,
        phase_5_21_l2v3d_suspected_root_cause: summary.suspected_root_cause,
        target_identity_mismatch_blocks_baseline_acceptance: summary.identity_mismatch_count > 0,
        renewed_baseline_requires_separate_baseline_acceptance: true,
        renewed_baseline_requires_separate_final_db_write_authorization: true,
        raw_write_ready_for_execution: false,
        raw_write_retry_authorization_status: 'blocked_pending_target_identity_reconciliation',
        next_required_step: summary.next_required_step,
    };
}

function tableRows(rows = []) {
    return rows.join('\n');
}

function buildComparisonRows(diagnostics = []) {
    return diagnostics.map(
        item =>
            `| ${item.requested_external_id} | ${item.requested_match_id} | ${item.requested_home_team}-${item.requested_away_team} | ${item.requested_kickoff_time} | ${item.request_url_summary || ''} | ${item.request_url_external_id || ''} | ${item.final_url_summary || ''} | ${item.final_url_external_id || ''} | ${item.http_status} | ${item.parsed} | ${item.observed_external_id || ''} | ${item.observed_match_identifier_fields?.general_matchId || ''} | ${item.observed_home_team || ''}-${item.observed_away_team || ''} | ${item.observed_match_time_utc || ''} | ${item.top_level_keys_summary.join(',')} | ${item.body_byte_length || 0}/${item.pageprops_json_byte_length || 0} | ${item.hash || ''} | ${item.identity_match} | ${item.mismatch_type} | ${item.safe_error_summary || ''} |`
    );
}

function buildReport({ summary = {}, diagnostics = [], manifestGate = {}, proposalGate = {} } = {}) {
    const comparisonRows = buildComparisonRows(diagnostics);
    const mismatchTypeLines = Object.entries(summary.mismatch_type_counts || {}).map(
        ([type, count]) => `- ${type}=${count}`
    );
    return `# Data Entrypoint Governance - Phase 5.21 L2V3D

## A. Current Status

- phase=target identity reconciliation planning
- branch=${summary.branch || 'unknown'}
- base_head=${summary.base_head || 'unknown'}
- main_head=${summary.main_head || 'unknown'}
- main_ci_status=${summary.main_ci_status || 'unknown'}
- no_write=true

## B. PR #1276 Merge Result

- pr_1276_state=${summary.pr_1276_state || 'MERGED'}
- pr_1276_merge_commit=${summary.pr_1276_merge_commit || 'unknown'}
- merge_scope=L2V3 / L2V3B No-Go + hash drift review documentation

## C. PR #1277 Rebase / Retarget / Merge Result

- pr_1277_state=${summary.pr_1277_state || 'MERGED'}
- pr_1277_merge_commit=${summary.pr_1277_merge_commit || 'unknown'}
- pr_1277_retarget_result=${summary.pr_1277_retarget_result || 'retargeted_to_main_before_merge'}
- merge_scope=L2V3C renewed baseline regeneration planning / no-write manifest proposal

## D. Authorization Scope

- planning_authorized=true
- target_identity_reconciliation_authorized=true
- network_recapture_authorized=true
- scope limited to L2V3C mismatch targets only
- no accepted baseline replacement
- no raw write authorization
- no DB write authorization

## E. No-Write Guarantee

- db_write_performed=false
- raw_insert_performed=false
- baseline_acceptance_performed=false
- raw_write_retry_performed=false
- full raw_data/pageProps/source body printed=false
- full raw_data/pageProps/source body saved=false

## F. L2V3C 8/8 Metadata Mismatch Recap

- source_proposal=${summary.renewed_baseline_proposal_path}
- l2v3c_checked_target_count=${summary.l2v3c_metadata_target_mismatch_count}
- l2v3c_metadata_target_mismatch_count=${proposalGate.checkedTargets?.length || 0}
- l2v3c_next_required_step=target_identity_reconciliation_planning
- raw_write_ready_for_execution=false
- requires_separate_baseline_acceptance=true
- requires_separate_final_db_write_authorization=true

## G. Target Identity Discovery Result

- candidate_targets_count=${manifestGate.candidate_targets_count || 0}
- known_completed_targets_count=${manifestGate.known_completed_targets_count || 0}
- checked_target_count=${summary.checked_target_count}
- identity_match_count=${summary.identity_match_count}
- identity_mismatch_count=${summary.identity_mismatch_count}
- deterministic_observed_identity_with_l2v3c=${summary.deterministic_observed_identity_with_l2v3c}
- deterministic_observed_identity_with_l2v3c_count=${summary.deterministic_observed_identity_with_l2v3c_count}
- deterministic_with_l2v3c=${summary.deterministic_with_l2v3c}
- deterministic_with_l2v3c_count=${summary.deterministic_with_l2v3c_count}

## H. Request URL / Route Construction Review

- route=${ROUTE}
- request_url_builder=buildFotMobMatchUrl(external_id)
- request_url_pattern=https://www.fotmob.com/match/{external_id}
- request_url_itself_wrong=${summary.request_url_itself_wrong}
- canonical_redirect_detected=${summary.canonical_redirect_detected}

## I. PageProps Extraction Review

- extraction_path=__NEXT_DATA__.props.pageProps
- stable_hash_function=computeStablePagePropsHash
- hash_strategy=${HASH_STRATEGY}
- parser_extractor_wrong_indicated=${summary.parser_extractor_wrong_indicated}
- full_pageProps_stored=false

## J. Requested vs Observed Metadata Comparison Summary

| requested_external_id | requested_match_id | requested_teams | requested_kickoff | request_url_summary | request_url_id | final_url_summary | final_url_id | http_status | parsed | observed_external_id | observed_general_matchId | observed_teams | observed_time_utc | top_level_keys | body/pageProps_bytes | hash | identity_match | mismatch_type | safe_error_summary |
| --------------------- | ------------------ | --------------- | ----------------- | ------------------- | -------------- | ----------------- | ------------ | ----------- | ------ | -------------------- | ------------------------ | -------------- | ----------------- | -------------- | -------------------- | ---- | -------------- | ------------- | ------------------ |
${tableRows(comparisonRows)}

## K. Mismatch Classification

- checked_target_count=${summary.checked_target_count}
- identity_match_count=${summary.identity_match_count}
- identity_mismatch_count=${summary.identity_mismatch_count}
- all_mismatches_same_pattern=${summary.all_mismatches_same_pattern}
- identity_mismatch_pattern_deterministic=${summary.deterministic_observed_identity_with_l2v3c}
- full_hash_and_identity_deterministic=${summary.deterministic_with_l2v3c}
${tableRows(mismatchTypeLines)}
- response_canonical_data_wrong_or_unexpected=${summary.response_canonical_data_wrong_or_unexpected}
- manifest_target_metadata_mismatch_indicated=${summary.manifest_target_metadata_mismatch_indicated}

## L. Root Cause Status

- root_cause_status=${summary.root_cause_status}
- suspected_root_cause=${summary.suspected_root_cause}
- concrete_root_cause_confirmed=${summary.root_cause_status?.startsWith('confirmed') === true}

## M. Required Fix / Continue Investigation Decision

- baseline_acceptance_blocked=true
- raw_write_retry_blocked=true
- code_fix_required=${summary.request_url_itself_wrong || summary.parser_extractor_wrong_indicated}
- manifest_or_source_inventory_reconciliation_required=${summary.manifest_target_metadata_mismatch_indicated}
- continue_investigation_required=${summary.root_cause_status !== 'confirmed_route_generation_mismatch'}

## N. DB Row Count Safety Result

- DB row counts must be verified with a separate SELECT-only check.
- expected_matches=${EXPECTED_ROW_COUNTS.matches}
- expected_raw_match_data=${EXPECTED_ROW_COUNTS.raw_match_data}
- expected_bookmaker_odds_history=${EXPECTED_ROW_COUNTS.bookmaker_odds_history}
- expected_l3_features=${EXPECTED_ROW_COUNTS.l3_features}
- expected_match_features_training=${EXPECTED_ROW_COUNTS.match_features_training}
- expected_predictions=${EXPECTED_ROW_COUNTS.predictions}
- candidate_fotmob_pageprops_v2_raw_rows_expected=0
- safety_status=pending_select_only_validation

## O. Test Results

- pending until local verification completes

## P. PR Status

- pending until PR is created

## Q. Next Step Recommendation

- next_required_step=${summary.next_required_step}
- target identity mismatch blocks baseline acceptance.
- raw write retry still requires separate final DB-write authorization after identity reconciliation.

## R. Explicit Non-Execution

- no DB writes
- no raw_match_data inserts
- no matches writes
- no bookmaker_odds_history writes
- no l3_features writes
- no match_features_training writes
- no predictions writes
- no schema migration
- no parser implementation
- no feature extraction
- no training/prediction
- no browser/proxy/captcha bypass
- no accepted baseline replacement
- no raw write retry
- no baseline_hash edits to pass a gate
- no proposal hash marked as accepted baseline
- no full raw_data/pageProps/source body print/save
- no invented external_id, match target, payload, or hash
- no L2V3/L2V3B/L2V3C evidence deletion
`;
}

async function diagnoseTargets(pairs = [], input = {}, dependencies = {}) {
    const diagnostics = [];
    for (let index = 0; index < pairs.length; index += 1) {
        const { target, proposalTarget } = pairs[index];
        diagnostics.push(await diagnoseTarget(target, proposalTarget, index, input, dependencies));
    }
    return diagnostics;
}

async function runPlanning(rawInput = {}, dependencies = {}) {
    const validation = validatePlanningInput(rawInput);
    if (!validation.ok) return { ok: false, status: 2, errors: validation.errors };
    const input = validation.input;
    const generatedAt = input.generatedAt || dependencies.generatedAt || new Date().toISOString();
    const manifest = dependencies.manifest || (dependencies.readJsonFile || readJsonFile)(input.manifest);
    const proposal = dependencies.renewedProposal || (dependencies.readJsonFile || readJsonFile)(input.renewedProposal);
    const manifestGate = validateManifestGate(manifest);
    if (!manifestGate.ok) return { ok: false, status: 3, errors: manifestGate.errors, manifest_gate: manifestGate };
    const proposalGate = validateRenewedProposalGate(proposal);
    if (!proposalGate.ok) return { ok: false, status: 4, errors: proposalGate.errors, proposal_gate: proposalGate };
    const selection = selectMismatchTargets(manifestGate, proposalGate, input.targetExternalIds);
    if (!selection.ok) return { ok: false, status: 5, errors: selection.errors };
    const diagnostics = await diagnoseTargets(selection.pairs, input, dependencies);
    const summary = buildSummary({ diagnostics, input, manifestGate, proposalGate, generatedAt });
    const updatedManifest = buildUpdatedManifest(manifest, summary);
    const report = buildReport({ summary, diagnostics, manifestGate, proposalGate });
    if (dependencies.writeManifest !== false) {
        (dependencies.writeManifestFile || dependencies.writeJsonFile || writeJsonFile)(
            input.manifest,
            updatedManifest
        );
    }
    if (dependencies.writeReport !== false) {
        (dependencies.writeReportFile || writeReportFile)(input.reportOutput, report);
    }
    return {
        ok: true,
        status: 0,
        summary,
        diagnostics,
        updated_manifest: updatedManifest,
        report,
        manifest_gate: manifestGate,
        proposal_gate: proposalGate,
        selected_external_ids: selection.selected_external_ids,
    };
}

async function runCli(argv = process.argv.slice(2), dependencies = {}) {
    const args = parseArgs(argv);
    if (args.help) {
        process.stdout.write(
            `Usage: node scripts/ops/pageprops_v2_target_identity_reconciliation_plan.js --manifest=${MANIFEST_PATH} --renewed-proposal=${RENEWED_PROPOSAL_PATH} ...\n`
        );
        return { status: 0 };
    }
    const result = await runPlanning(args, dependencies);
    const output = result.ok
        ? {
              ok: true,
              status: result.status,
              summary: result.summary,
              selected_external_ids: result.selected_external_ids,
          }
        : { ok: false, status: result.status, errors: result.errors };
    process.stdout.write(`${JSON.stringify(output, null, 2)}\n`);
    return { status: result.status };
}

module.exports = {
    PHASE,
    MANIFEST_PATH,
    RENEWED_PROPOSAL_PATH,
    REPORT_PATH,
    SOURCE,
    ROUTE,
    LEAGUE_ID,
    LEAGUE_NAME,
    SEASON,
    BATCH_ID,
    RAW_VERSION,
    HASH_STRATEGY,
    TARGET_COUNT,
    EXPECTED_MISMATCH_COUNT,
    EXPECTED_ROW_COUNTS,
    parseArgs,
    normalizeBooleanFlag,
    validatePlanningInput,
    validateManifestGate,
    validateRenewedProposalGate,
    extractSafeIdentityFromPageProps,
    classifyDiagnostic,
    selectMismatchTargets,
    diagnoseTarget,
    diagnoseTargets,
    buildSummary,
    buildUpdatedManifest,
    buildReport,
    runPlanning,
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
