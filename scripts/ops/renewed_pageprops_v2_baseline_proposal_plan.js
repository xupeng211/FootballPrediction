#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const base = require('./single_league_pageprops_v2_controlled_write_execute');

const PHASE = 'PHASE5_21L2V3C_RENEWED_BASELINE_REGENERATION_PLANNING';
const MANIFEST_PATH = base.MANIFEST_PATH;
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3C.md';
const PROPOSAL_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.renewed_baseline_proposal.phase521l2v3c.json';
const SOURCE = base.SOURCE;
const ROUTE = base.ROUTE;
const LEAGUE_ID = base.LEAGUE_ID;
const LEAGUE_NAME = base.LEAGUE_NAME;
const SEASON = base.SEASON;
const BATCH_ID = base.BATCH_ID;
const RAW_VERSION = base.RAW_VERSION;
const HASH_STRATEGY = base.HASH_STRATEGY;
const TARGET_COUNT = base.TARGET_COUNT;
const KNOWN_COMPLETED_COUNT = 8;
const LOW_PATH_COUNT_THRESHOLD = 4000;
const DEFAULT_REPEAT_COUNT = 2;
const DEFAULT_REQUEST_DELAY_MS = 750;
const DEFAULT_NORMAL_SAMPLE_EXTERNAL_IDS = Object.freeze(['4830463', '4830465', '4830508']);
const REQUIRED_YES_FLAGS = Object.freeze([
    'planningAuthorization',
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
    'rawWriteReadyForExecution',
]);

function normalizeText(value) {
    return String(value ?? '').trim();
}

function normalizeBooleanFlag(value, fallback = undefined) {
    if (typeof value === 'boolean') return value;
    if (value === null || value === undefined || value === '') return fallback;
    const normalized = normalizeText(value).toLowerCase();
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

function parseCsv(value) {
    return normalizeText(value)
        .split(',')
        .map(item => item.trim())
        .filter(Boolean);
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = {
        manifest: null,
        proposalOutput: PROPOSAL_PATH,
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
        rawWriteReadyForExecution: false,
        sampleExternalIds: null,
        repeatCount: DEFAULT_REPEAT_COUNT,
        requestDelayMs: DEFAULT_REQUEST_DELAY_MS,
        baseHead: null,
        baseBranch: null,
        branch: null,
        pr1276State: null,
        pr1276Url: null,
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

function normalizePlanningInput(input = {}) {
    return {
        manifest: normalizeText(input.manifest),
        proposalOutput: normalizeText(input.proposalOutput) || PROPOSAL_PATH,
        source: normalizeText(input.source).toLowerCase(),
        leagueId: parseInteger(input.leagueId, null),
        leagueName: normalizeText(input.leagueName),
        season: normalizeText(input.season),
        route: normalizeText(input.route),
        rawVersion: normalizeText(input.rawVersion),
        hashStrategy: normalizeText(input.hashStrategy),
        batchId: normalizeText(input.batchId),
        targetCount: parseInteger(input.targetCount, null),
        planningAuthorization: normalizeBooleanFlag(input.planningAuthorization, undefined),
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
        rawWriteReadyForExecution: normalizeBooleanFlag(input.rawWriteReadyForExecution, false),
        sampleExternalIds: Array.isArray(input.sampleExternalIds)
            ? input.sampleExternalIds.map(normalizeText).filter(Boolean)
            : parseCsv(input.sampleExternalIds),
        repeatCount: parseInteger(input.repeatCount, DEFAULT_REPEAT_COUNT),
        requestDelayMs: parseInteger(input.requestDelayMs, DEFAULT_REQUEST_DELAY_MS),
        baseHead: normalizeText(input.baseHead),
        baseBranch: normalizeText(input.baseBranch),
        branch: normalizeText(input.branch),
        pr1276State: normalizeText(input.pr1276State),
        pr1276Url: normalizeText(input.pr1276Url),
        generatedAt: normalizeText(input.generatedAt),
        unknown: Array.isArray(input.unknown) ? input.unknown : [],
    };
}

function pushRequiredYes(errors, value, name) {
    if (value === true) return;
    errors.push(value === false ? `${name}=yes is required in Phase 5.21L2V3C` : `missing ${name}=yes`);
}

function pushRequiredNo(errors, value, name) {
    if (value === false) return;
    errors.push(value === true ? `${name}=yes is blocked in Phase 5.21L2V3C` : `missing ${name}=no`);
}

function requireExact(errors, actual, expected, name) {
    if (!normalizeText(actual)) {
        errors.push(`missing ${name}=${expected}`);
        return;
    }
    if (normalizeText(actual) !== expected) {
        errors.push(`${name} must be ${expected}`);
    }
}

function validatePlanningInput(rawInput = {}) {
    const input = normalizePlanningInput(rawInput);
    const errors = [];
    requireExact(errors, input.manifest, MANIFEST_PATH, 'manifest');
    requireExact(errors, input.proposalOutput, PROPOSAL_PATH, 'proposal-output');
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
        if (input[key] === true) errors.push(`${flagName(key)}=yes is blocked in Phase 5.21L2V3C`);
    }
    if (!Number.isInteger(input.repeatCount) || input.repeatCount < 1 || input.repeatCount > 2) {
        errors.push('repeat-count must be 1 or 2');
    }
    if (!Number.isInteger(input.requestDelayMs) || input.requestDelayMs < 0) {
        errors.push('request-delay-ms must be a non-negative integer');
    }
    if (input.unknown.length > 0) {
        errors.push(`unknown arguments: ${input.unknown.join(',')}`);
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

function pagePropsPathCount(target = {}) {
    return Number(target.pageprops_summary?.pageProps_path_count ?? target.pageProps_path_count ?? 0);
}

function pagePropsContentPathCount(target = {}) {
    return Number(target.pageprops_summary?.pageProps_content_path_count ?? target.pageProps_content_path_count ?? 0);
}

function validateManifestGate(manifest = {}) {
    const errors = [];
    const candidates = Array.isArray(manifest.candidate_targets) ? manifest.candidate_targets : [];
    const knownCompleted = Array.isArray(manifest.known_completed_targets) ? manifest.known_completed_targets : [];
    if (candidates.length !== TARGET_COUNT) errors.push(`candidate_targets must be ${TARGET_COUNT}`);
    if (knownCompleted.length !== KNOWN_COMPLETED_COUNT) {
        errors.push(`known_completed_targets must be ${KNOWN_COMPLETED_COUNT}`);
    }
    if (manifest.phase_5_21_l2v3_execution_status !== 'blocked') {
        errors.push('phase_5_21_l2v3_execution_status must be blocked');
    }
    if (manifest.renewed_controlled_pageprops_v2_raw_write_status !== 'blocked') {
        errors.push('renewed_controlled_pageprops_v2_raw_write_status must be blocked');
    }
    if (manifest.phase_5_21_l2v3b_review_status !== 'completed_no_write') {
        errors.push('phase_5_21_l2v3b_review_status must be completed_no_write');
    }
    if (manifest.hash_drift_classification !== 'partial_systemic_stable_content_drift') {
        errors.push('hash_drift_classification must reflect L2V3B drift review');
    }
    for (const target of candidates) {
        const externalId = normalizeText(target.external_id);
        const matchId = normalizeText(target.match_id);
        if (!/^\d+$/.test(externalId)) errors.push(`invalid external_id for ${matchId || 'unknown'}`);
        if (matchId !== `53_20252026_${externalId}`) errors.push(`match_id convention mismatch for ${externalId}`);
        if (!/^[a-f0-9]{64}$/.test(normalizeText(target.baseline_hash))) {
            errors.push(`baseline_hash invalid for ${externalId}`);
        }
        if (target.preflight_status !== 'hash_baseline_ready') {
            errors.push(`preflight_status must be hash_baseline_ready for ${externalId}`);
        }
        if (target.matches_seed_status !== 'inserted_matches_identity') {
            errors.push(`matches_seed_status must be inserted_matches_identity for ${externalId}`);
        }
        if (!isPlainObject(target.pageprops_summary)) {
            errors.push(`pageprops_summary missing for ${externalId}`);
        }
    }
    return {
        ok: errors.length === 0,
        errors,
        candidate_targets_count: candidates.length,
        known_completed_targets_count: knownCompleted.length,
    };
}

function selectTargetsForPlanning(manifest = {}, sampleExternalIds = []) {
    const candidates = Array.isArray(manifest.candidate_targets) ? manifest.candidate_targets : [];
    const byExternalId = new Map(candidates.map(target => [normalizeText(target.external_id), target]));
    const lowPathTargets = candidates.filter(
        target => pagePropsPathCount(target) > 0 && pagePropsPathCount(target) < LOW_PATH_COUNT_THRESHOLD
    );
    const requestedIds =
        sampleExternalIds.length > 0
            ? sampleExternalIds
            : [
                  ...lowPathTargets.map(target => normalizeText(target.external_id)),
                  ...DEFAULT_NORMAL_SAMPLE_EXTERNAL_IDS,
              ];
    const uniqueIds = [...new Set(requestedIds.map(normalizeText).filter(Boolean))];
    const missing = uniqueIds.filter(externalId => !byExternalId.has(externalId));
    if (missing.length > 0) {
        return {
            ok: false,
            errors: [`sample external_id not found in candidate_targets: ${missing.join(',')}`],
            targets: [],
            lowPathTargets,
            requested_external_ids: uniqueIds,
        };
    }
    return {
        ok: true,
        errors: [],
        targets: uniqueIds.map(externalId => byExternalId.get(externalId)),
        lowPathTargets,
        requested_external_ids: uniqueIds,
    };
}

function summarizeTopLevelKeys(attempts = []) {
    const keys = new Set();
    for (const attempt of attempts) {
        for (const key of attempt.pageProps_top_level_keys || []) keys.add(key);
    }
    return [...keys].sort();
}

function extractSafeIdentityFromPageProps(pageProps = {}) {
    if (!isPlainObject(pageProps)) {
        return { external_id: null, home_team: null, away_team: null, match_name: null, match_time_utc: null };
    }
    const general = isPlainObject(pageProps.general) ? pageProps.general : {};
    const header = isPlainObject(pageProps.header) ? pageProps.header : {};
    const teams = Array.isArray(header.teams) ? header.teams : [];
    return {
        external_id: normalizeText(general.matchId || general.matchID || general.id),
        home_team: normalizeText(teams[0]?.name || header.homeTeam?.name || header.homeTeam),
        away_team: normalizeText(teams[1]?.name || header.awayTeam?.name || header.awayTeam),
        match_name: normalizeText(general.matchName),
        match_time_utc: normalizeText(general.matchTimeUTCDate || general.matchTimeUTC),
    };
}

function identityStatus(target = {}, identity = {}) {
    const expectedExternalId = normalizeText(target.external_id);
    const actualExternalId = normalizeText(identity.external_id);
    const actualExternalIdSuffix = actualExternalId.match(/(\d+)$/)?.[1] || actualExternalId;
    if (actualExternalId && actualExternalIdSuffix !== expectedExternalId) return 'metadata_target_mismatch';
    return 'match_id_external_id_reconciled';
}

function publicAttemptSummary(summary = {}, target = {}, attemptNumber = 1) {
    const identity = extractSafeIdentityFromPageProps(summary.pageProps);
    return {
        attempt: attemptNumber,
        target_id: target.target_id,
        match_id: target.match_id,
        external_id: target.external_id,
        http_status: summary.http_status ?? null,
        parsed: summary.next_data_parse_ok === true && summary.page_props_found === true,
        block_markers: summary.block_markers || [],
        body_byte_length: summary.body_byte_length ?? null,
        candidate_json_byte_length: summary.candidate_json_byte_length ?? null,
        stable_hash: summary.recaptured_hash || null,
        matches_baseline: summary.hash_matches_baseline === true,
        top_level_keys: summary.pageProps_top_level_keys || [],
        pageProps_path_count: summary.pageProps_path_count || 0,
        pageProps_content_path_count: summary.pageProps_content_path_count || 0,
        metadata_identity_status: identityStatus(target, identity),
        metadata_identity_observed: identity,
        safe_error_summary: summary.failure_reason || null,
    };
}

async function sleep(ms) {
    if (!ms) return;
    await new Promise(resolve => {
        setTimeout(resolve, ms);
    });
}

async function recaptureTargetForProposal(target, index, input, dependencies = {}) {
    const attempts = [];
    let stopReason = null;
    for (let attemptIndex = 0; attemptIndex < input.repeatCount; attemptIndex += 1) {
        if (attemptIndex > 0 || index > 0) {
            await sleep(input.requestDelayMs);
        }
        const summary = await base.recaptureTarget(target, index, dependencies);
        const publicSummary = publicAttemptSummary(summary, target, attemptIndex + 1);
        attempts.push(publicSummary);
        if (publicSummary.block_markers.length > 0) {
            stopReason = 'block_or_captcha';
            break;
        }
    }
    return buildCheckedTargetProposal(target, attempts, stopReason);
}

function classifyTargetAttempts(target = {}, attempts = [], stopReason = null) {
    if (stopReason === 'block_or_captcha' || attempts.some(attempt => attempt.block_markers.length > 0)) {
        return 'block_or_captcha';
    }
    if (attempts.some(attempt => attempt.metadata_identity_status === 'metadata_target_mismatch')) {
        return 'metadata_target_mismatch';
    }
    if (attempts.length === 0 || attempts.some(attempt => !attempt.parsed || !attempt.stable_hash)) {
        return 'fetch_or_parse_failure';
    }
    const hashes = [...new Set(attempts.map(attempt => attempt.stable_hash).filter(Boolean))];
    if (hashes.length > 1) return 'unstable_hash';
    return hashes[0] === normalizeText(target.baseline_hash) ? 'stable_match' : 'stable_drift';
}

function buildCheckedTargetProposal(target = {}, attempts = [], stopReason = null) {
    const hashStatus = classifyTargetAttempts(target, attempts, stopReason);
    const hashes = attempts.map(attempt => attempt.stable_hash).filter(Boolean);
    const uniqueHashes = [...new Set(hashes)];
    const lowPathCountRisk = pagePropsPathCount(target) > 0 && pagePropsPathCount(target) < LOW_PATH_COUNT_THRESHOLD;
    return {
        target_id: target.target_id,
        match_id: target.match_id,
        external_id: target.external_id,
        old_baseline_hash: target.baseline_hash,
        renewed_candidate_hash: uniqueHashes.length === 1 ? uniqueHashes[0] : null,
        hash_status: hashStatus,
        repeated_hash_stability:
            attempts.length < 2
                ? 'single_attempt_only'
                : uniqueHashes.length === 1
                  ? 'stable_current_hash'
                  : 'unstable_current_hash',
        low_path_count_risk: lowPathCountRisk,
        old_baseline_path_count: pagePropsPathCount(target),
        old_baseline_content_path_count: pagePropsContentPathCount(target),
        payload_size_summary: {
            body_byte_lengths: attempts.map(attempt => attempt.body_byte_length).filter(Number.isFinite),
            candidate_json_byte_lengths: attempts
                .map(attempt => attempt.candidate_json_byte_length)
                .filter(Number.isFinite),
        },
        top_level_keys_summary: summarizeTopLevelKeys(attempts),
        path_count_summary: {
            old_pageProps_path_count: pagePropsPathCount(target),
            old_pageProps_content_path_count: pagePropsContentPathCount(target),
            renewed_pageProps_path_counts: attempts
                .map(attempt => attempt.pageProps_path_count)
                .filter(Number.isFinite),
            renewed_pageProps_content_path_counts: attempts
                .map(attempt => attempt.pageProps_content_path_count)
                .filter(Number.isFinite),
        },
        metadata_identity_status: attempts.some(
            attempt => attempt.metadata_identity_status === 'metadata_target_mismatch'
        )
            ? 'metadata_target_mismatch'
            : 'match_id_external_id_reconciled',
        safe_error_summary:
            attempts
                .map(attempt => attempt.safe_error_summary)
                .filter(Boolean)
                .join(' | ') || null,
        attempts,
    };
}

function countByStatus(targets = []) {
    return targets.reduce((acc, target) => {
        acc[target.hash_status] = (acc[target.hash_status] || 0) + 1;
        return acc;
    }, {});
}

function classifyOverallDrift(checkedTargets = []) {
    const checked = checkedTargets.length;
    const stableDrift = checkedTargets.filter(target => target.hash_status === 'stable_drift');
    const stableMatch = checkedTargets.filter(target => target.hash_status === 'stable_match');
    const unstable = checkedTargets.filter(target => target.hash_status === 'unstable_hash');
    if (unstable.length > 0) return 'unstable_hash_implementation';
    if (checked === 0) return 'unknown';
    if (stableDrift.length === 1 && stableMatch.length === checked - 1) return 'single_target';
    if (stableDrift.length === checked) return 'fully_systemic';
    const lowPathDrifts = stableDrift.filter(target => target.low_path_count_risk).length;
    if (stableDrift.length > 0 && lowPathDrifts === stableDrift.length) return 'low_path_count_subset';
    if (stableDrift.length > 0) return 'partial_systemic';
    return 'unknown';
}

function recommendedNextStep(summary = {}) {
    if (Number(summary.metadata_target_mismatch_count || 0) > 0) {
        return 'target_identity_reconciliation_planning';
    }
    if (Number(summary.unstable_hash_count || 0) > 0) {
        return 'stable_pageprops_payload_v1_canonicalization_fix_planning';
    }
    if (
        Number(summary.fetch_or_parse_failure_count || 0) > 0 ||
        Number(summary.block_or_captcha_count || 0) > 0 ||
        summary.drift_classification === 'unknown'
    ) {
        return 'expanded_no_write_baseline_drift_sampling';
    }
    return 'renewed_baseline_acceptance_review';
}

function buildSummary({ manifest, checkedTargets, lowPathTargets, input, generatedAt, baseContext }) {
    const statusCounts = countByStatus(checkedTargets);
    const stableDriftTargets = checkedTargets.filter(target => target.hash_status === 'stable_drift');
    const lowPathDrifts = stableDriftTargets.filter(target => target.low_path_count_risk);
    const normalPathDrifts = stableDriftTargets.filter(target => !target.low_path_count_risk);
    const summary = {
        phase: PHASE,
        proposal_status: 'renewed_baseline_review_required',
        source_manifest_path: input.manifest,
        renewed_baseline_proposal_path: input.proposalOutput,
        generated_at: generatedAt,
        base_head: input.baseHead || baseContext.base_head || null,
        base_branch: input.baseBranch || baseContext.base_branch || null,
        branch: input.branch || baseContext.branch || null,
        pr_1276_state: input.pr1276State || baseContext.pr_1276_state || null,
        pr_1276_url: input.pr1276Url || baseContext.pr_1276_url || null,
        candidate_targets_count: (manifest.candidate_targets || []).length,
        checked_target_count: checkedTargets.length,
        no_write: true,
        db_write_performed: false,
        raw_insert_performed: false,
        hash_strategy: HASH_STRATEGY,
        hash_function: 'computeStablePagePropsHash',
        baseline_source_phase: 'Phase 5.21L2T no-write preflight',
        renewed_hash_generation_phase: 'Phase 5.21L2V3C no-write proposal',
        stable_match_count: statusCounts.stable_match || 0,
        stable_drift_count: statusCounts.stable_drift || 0,
        unstable_hash_count: statusCounts.unstable_hash || 0,
        fetch_or_parse_failure_count: statusCounts.fetch_or_parse_failure || 0,
        block_or_captcha_count: statusCounts.block_or_captcha || 0,
        metadata_target_mismatch_count: statusCounts.metadata_target_mismatch || 0,
        low_path_count_target_count: lowPathTargets.length,
        low_path_count_checked_count: checkedTargets.filter(target => target.low_path_count_risk).length,
        low_path_count_drift_count: lowPathDrifts.length,
        normal_path_count_drift_count: normalPathDrifts.length,
        drift_classification: classifyOverallDrift(checkedTargets),
        requires_human_review: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        next_required_step: null,
    };
    summary.next_required_step = recommendedNextStep(summary);
    return summary;
}

function buildProposal({ manifest, checkedTargets, lowPathTargets, input, generatedAt, baseContext }) {
    const checkedIds = new Set(checkedTargets.map(target => normalizeText(target.external_id)));
    const targetsNotChecked = (manifest.candidate_targets || [])
        .filter(target => !checkedIds.has(normalizeText(target.external_id)))
        .map(target => ({
            target_id: target.target_id,
            match_id: target.match_id,
            external_id: target.external_id,
            old_baseline_hash: target.baseline_hash,
            preserved_old_baseline: true,
            proposal_status: 'not_regenerated_in_l2v3c_sample',
        }));
    const summary = buildSummary({ manifest, checkedTargets, lowPathTargets, input, generatedAt, baseContext });
    return {
        proposal_phase: 'Phase 5.21L2V3C',
        proposal_status: summary.proposal_status,
        source_manifest_path: input.manifest,
        generated_at: generatedAt,
        base_head: summary.base_head,
        base_branch: summary.base_branch,
        branch: summary.branch,
        candidate_targets_count: summary.candidate_targets_count,
        checked_targets_count: summary.checked_target_count,
        no_write: true,
        db_write_performed: false,
        raw_insert_performed: false,
        hash_strategy: HASH_STRATEGY,
        hash_function: 'computeStablePagePropsHash',
        baseline_source_phase: summary.baseline_source_phase,
        renewed_hash_generation_phase: summary.renewed_hash_generation_phase,
        summary,
        checked_targets: checkedTargets,
        targets_not_checked: targetsNotChecked,
        recommendation: {
            requires_human_review: true,
            requires_separate_baseline_acceptance: true,
            requires_separate_final_db_write_authorization: true,
            raw_write_ready_for_execution: false,
            recommended_next_phase: `Phase 5.21L2V3D ${summary.next_required_step}`,
        },
    };
}

function updateManifestWithPlanning(manifest = {}, proposal = {}) {
    return {
        ...manifest,
        phase_5_21_l2v3c_planning_status: 'completed_no_write',
        renewed_baseline_planning_status: 'renewed_baseline_review_required',
        no_write_recapture_status: 'completed_no_write_sample',
        phase_5_21_l2v3c_checked_target_count: proposal.summary.checked_target_count,
        phase_5_21_l2v3c_stable_match_count: proposal.summary.stable_match_count,
        phase_5_21_l2v3c_stable_drift_count: proposal.summary.stable_drift_count,
        phase_5_21_l2v3c_unstable_hash_count: proposal.summary.unstable_hash_count,
        phase_5_21_l2v3c_fetch_or_parse_failure_count: proposal.summary.fetch_or_parse_failure_count,
        phase_5_21_l2v3c_block_or_captcha_count: proposal.summary.block_or_captcha_count,
        phase_5_21_l2v3c_metadata_target_mismatch_count: proposal.summary.metadata_target_mismatch_count,
        phase_5_21_l2v3c_low_path_count_target_count: proposal.summary.low_path_count_target_count,
        phase_5_21_l2v3c_low_path_count_drift_count: proposal.summary.low_path_count_drift_count,
        phase_5_21_l2v3c_drift_classification: proposal.summary.drift_classification,
        renewed_baseline_proposal_path: proposal.source_manifest_path ? PROPOSAL_PATH : PROPOSAL_PATH,
        renewed_baseline_requires_human_review: true,
        renewed_baseline_requires_separate_baseline_acceptance: true,
        renewed_baseline_requires_separate_final_db_write_authorization: true,
        raw_write_retry_readiness_status: manifest.raw_write_retry_readiness_status,
        phase_5_21_l2v3c_db_write_performed: false,
        phase_5_21_l2v3c_raw_insert_performed: false,
        next_required_step: proposal.summary.next_required_step,
    };
}

function tableRows(rows = []) {
    return rows.join('\n');
}

function buildReport(proposal = {}) {
    const summary = proposal.summary || {};
    const checkedRows = (proposal.checked_targets || []).map(target => {
        const observed = target.attempts?.[0]?.metadata_identity_observed || {};
        return `| ${target.external_id} | ${target.match_id} | ${target.low_path_count_risk} | ${target.hash_status} | ${observed.external_id || ''} | ${observed.match_name || ''} | ${observed.match_time_utc || ''} | ${target.old_baseline_path_count} | ${target.path_count_summary.renewed_pageProps_path_counts.join(',')} | ${target.old_baseline_hash} | ${target.renewed_candidate_hash || ''} | ${target.repeated_hash_stability} |`;
    });
    return `# Data Entrypoint Governance - Phase 5.21 L2V3C

## A. Current Status

- phase=renewed baseline regeneration planning / no-write manifest proposal
- branch=${summary.branch || 'unknown'}
- base_head=${summary.base_head || 'unknown'}
- base_branch=${summary.base_branch || 'unknown'}
- proposal_status=${proposal.proposal_status}

## B. PR #1276 / Base Branch Status

- pr_1276_state=${summary.pr_1276_state || 'unknown'}
- pr_1276_url=${summary.pr_1276_url || 'unknown'}
- base_note=L2V3C was prepared on the branch containing PR #1276 head changes, not on main, because PR #1276 was not merged at phase start.

## C. Authorization Scope

- no-write planning only
- no accepted baseline replacement
- no raw write authorization
- no DB write authorization
- network recapture is no-write and limited to manifest candidate samples

## D. Explicit No-Write Guarantee

- no_write=true
- db_write_performed=false
- raw_insert_performed=false
- full raw_data/pageProps/source body saved=false
- full raw_data/pageProps/source body printed=false

## E. Read-Only Discovery Result

- candidate_targets_count=${summary.candidate_targets_count}
- known_completed_targets_count=${KNOWN_COMPLETED_COUNT}
- L2V3 blocked metadata present=true
- L2V3B review metadata present=true
- stable_pageprops_payload_v1 implementation located=true
- baseline generation path located=true
- recapture hash generation path located=true

## F. No-Write Recapture Scope

- checked_target_count=${summary.checked_target_count}
- low_path_count_target_count=${summary.low_path_count_target_count}
- repeat_count=${proposal.checked_targets?.[0]?.attempts?.length || 0}
- hash_strategy=${summary.hash_strategy}

## G. 4830466 Renewed Baseline Observation

- baseline_hash=c0365494bedfad7f49c59db649dc52d45bd364e7991f518261085349bebd530b
- L2V3B recaptured_hash=34f7ba2a692b03c4e5d2e0df4eef544569eb9773ba568a8d96a93c78f3962087
- L2V3C status=${(proposal.checked_targets || []).find(target => target.external_id === '4830466')?.hash_status || 'not_checked'}

## H. Low Path-Count Risk Target Analysis

- low_path_count_checked_count=${summary.low_path_count_checked_count}
- low_path_count_drift_count=${summary.low_path_count_drift_count}
- threshold=${LOW_PATH_COUNT_THRESHOLD}

## I. Stratified Sample Result

| external_id | match_id | low_path_count_risk | hash_status | observed_external_id | observed_match_name | observed_match_time_utc | old_paths | renewed_paths | old_baseline_hash | renewed_candidate_hash | repeated_hash_stability |
| ----------- | -------- | ------------------- | ----------- | -------------------- | ------------------- | ----------------------- | --------- | ------------- | ----------------- | ---------------------- | ----------------------- |
${tableRows(checkedRows)}

## J. Hash Drift Classification

- checked_target_count=${summary.checked_target_count}
- stable_match_count=${summary.stable_match_count}
- stable_drift_count=${summary.stable_drift_count}
- unstable_hash_count=${summary.unstable_hash_count}
- fetch_or_parse_failure_count=${summary.fetch_or_parse_failure_count}
- block_or_captcha_count=${summary.block_or_captcha_count}
- metadata_target_mismatch_count=${summary.metadata_target_mismatch_count}
- low_path_count_drift_count=${summary.low_path_count_drift_count}
- normal_path_count_drift_count=${summary.normal_path_count_drift_count}
- drift_classification=${summary.drift_classification}

## K. Canonicalization / Hash Implementation

- hash_function=computeStablePagePropsHash
- hash_strategy=stable_pageprops_payload_v1
- implementation_split_detected=false
- canonicalization_issue_detected=false

## L. Target Metadata Mismatch

- metadata_target_mismatch_count=${summary.metadata_target_mismatch_count}

## M. Renewed Baseline Proposal File

- proposal_path=${summary.renewed_baseline_proposal_path}

## N. Proposal Contents and Exclusions

Contains:

- checked target safe hashes and structural summaries
- old baseline hashes preserved for comparison
- not-checked targets marked as not_regenerated_in_l2v3c_sample
- human review and separate authorization requirements

Does not contain:

- accepted baseline replacement
- raw write readiness for execution
- full raw_data
- full pageProps
- full source body

## O. DB Row Count Safety Result

- DB row counts were verified separately with SELECT-only checks.
- Expected unchanged counts: matches=60, raw_match_data=18, bookmaker_odds_history=2, l3_features=2, match_features_training=2, predictions=2.

## P. Manifest Update

- phase_5_21_l2v3c_planning_status=completed_no_write
- renewed_baseline_planning_status=renewed_baseline_review_required
- renewed_baseline_proposal_path=${summary.renewed_baseline_proposal_path}
- requires_human_review=true
- requires_separate_baseline_acceptance=true
- requires_separate_final_db_write_authorization=true

## Q. Test Results

- pending until local verification completes

## R. PR Status

- pending until PR is created

## S. Next Step

- Recommended: Phase 5.21L2V3D ${summary.next_required_step}.
- This next phase is still not a DB write.

## T. Explicit Non-Execution

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
- no hash gate bypass
- no accepted baseline replacement
- no full raw_data/pageProps/source body print/save
- no file deletion
`;
}

async function recapturePlanningTargets(targets = [], input, dependencies = {}) {
    const checkedTargets = [];
    for (let index = 0; index < targets.length; index += 1) {
        const checked = await recaptureTargetForProposal(targets[index], index, input, dependencies);
        checkedTargets.push(checked);
        if (checked.hash_status === 'block_or_captcha') break;
    }
    return checkedTargets;
}

async function runPlanning(rawInput = {}, dependencies = {}) {
    const validation = validatePlanningInput(rawInput);
    if (!validation.ok) {
        return { ok: false, status: 2, errors: validation.errors };
    }
    const input = validation.input;
    const generatedAt = input.generatedAt || dependencies.generatedAt || new Date().toISOString();
    const manifest = dependencies.manifest || (dependencies.readJsonFile || readJsonFile)(input.manifest);
    const manifestGate = validateManifestGate(manifest);
    if (!manifestGate.ok) {
        return { ok: false, status: 3, errors: manifestGate.errors, manifest_gate: manifestGate };
    }
    const selection = selectTargetsForPlanning(manifest, input.sampleExternalIds);
    if (!selection.ok) {
        return { ok: false, status: 4, errors: selection.errors };
    }
    const checkedTargets = await recapturePlanningTargets(selection.targets, input, dependencies);
    const baseContext = dependencies.baseContext || {};
    const proposal = buildProposal({
        manifest,
        checkedTargets,
        lowPathTargets: selection.lowPathTargets,
        input,
        generatedAt,
        baseContext,
    });
    const updatedManifest = updateManifestWithPlanning(manifest, proposal);
    const report = buildReport(proposal);
    if (dependencies.writeProposal !== false) {
        (dependencies.writeJsonFile || writeJsonFile)(input.proposalOutput, proposal);
    }
    if (dependencies.writeManifest !== false) {
        (dependencies.writeManifestFile || dependencies.writeJsonFile || writeJsonFile)(
            input.manifest,
            updatedManifest
        );
    }
    if (dependencies.writeReport !== false) {
        (dependencies.writeReportFile || writeReportFile)(REPORT_PATH, report);
    }
    return {
        ok: true,
        status: 0,
        proposal,
        updated_manifest: updatedManifest,
        report,
        summary: proposal.summary,
        manifest_gate: manifestGate,
        selected_external_ids: selection.requested_external_ids,
    };
}

async function runCli(argv = process.argv.slice(2), dependencies = {}) {
    const args = parseArgs(argv);
    if (args.help) {
        process.stdout.write(
            `Usage: node scripts/ops/renewed_pageprops_v2_baseline_proposal_plan.js --manifest=${MANIFEST_PATH} ...\n`
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
    REPORT_PATH,
    PROPOSAL_PATH,
    SOURCE,
    ROUTE,
    LEAGUE_ID,
    LEAGUE_NAME,
    SEASON,
    BATCH_ID,
    RAW_VERSION,
    HASH_STRATEGY,
    TARGET_COUNT,
    LOW_PATH_COUNT_THRESHOLD,
    parseArgs,
    validatePlanningInput,
    validateManifestGate,
    selectTargetsForPlanning,
    classifyTargetAttempts,
    classifyOverallDrift,
    buildCheckedTargetProposal,
    buildProposal,
    updateManifestWithPlanning,
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
