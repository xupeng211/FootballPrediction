#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const l2v3e = require('./pageprops_v2_target_source_inventory_reconciliation_plan');

const PHASE = 'PHASE5_21L2V3F_SCHEDULE_DETAIL_IDENTITY_NORMALIZATION_FIX_PLANNING';
const MANIFEST_PATH = l2v3e.MANIFEST_PATH;
const RENEWED_PROPOSAL_PATH = l2v3e.RENEWED_PROPOSAL_PATH;
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3F.md';
const NORMALIZATION_PROPOSAL_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.schedule_detail_identity_normalization_proposal.phase521l2v3f.json';
const SOURCE_RECONCILIATION_REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3E.md';
const SOURCE = l2v3e.SOURCE;
const LEAGUE_ID = l2v3e.LEAGUE_ID;
const LEAGUE_NAME = l2v3e.LEAGUE_NAME;
const SEASON = l2v3e.SEASON;
const RAW_VERSION = l2v3e.RAW_VERSION;
const HASH_STRATEGY = l2v3e.HASH_STRATEGY;
const BATCH_ID = l2v3e.BATCH_ID;
const TARGET_COUNT = l2v3e.TARGET_COUNT;
const EXPECTED_CHECKED_TARGET_COUNT = l2v3e.EXPECTED_MISMATCH_COUNT;
const EXPECTED_ROW_COUNTS = l2v3e.EXPECTED_ROW_COUNTS;

const REQUIRED_YES_FLAGS = Object.freeze([
    'planningAuthorization',
    'scheduleDetailNormalizationAuthorization',
    'networkAuthorization',
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
    'acceptBaseline',
    'acceptedBaseline',
    'acceptIdentityMapping',
    'identityMappingAcceptance',
    'baselineAcceptanceAuthorization',
    'rawWriteReadyForExecution',
    'rawWriteRetryAuthorization',
    'allowOddsWrite',
    'executeWrite',
    'commit',
    'inventTargets',
    'fabricateExternalIds',
]);

const ALLOWED_NEXT_STEPS = new Set([
    'schedule_detail_identity_normalization_fix_planning',
    'schedule_detail_identity_mapping_acceptance_review',
    'expanded no-write schedule detail normalization proposal',
    'schedule_detail_route_normalization_fix_implementation_planning',
    'continued target identity investigation',
]);

const ALLOWED_L2V3E_STATUS = new Set([
    'blocked_schedule_detail_identity_mismatch_identified',
    'blocked_schedule_detail_identity_normalization_proposal_only',
    'blocked_schedule_detail_route_normalization_fix_planning_required',
    'blocked_schedule_detail_expanded_proposal_required',
    'blocked_schedule_detail_identity_investigation_continues',
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

function toCamelKey(rawKey) {
    return normalizeText(rawKey).replace(/[-_]([a-z0-9])/g, (_match, char) => char.toUpperCase());
}

function flagName(key) {
    return key.replace(/[A-Z]/g, char => `-${char.toLowerCase()}`);
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = {
        manifest: null,
        renewedProposal: null,
        reportOutput: null,
        normalizationProposalOutput: null,
        sourceInventoryReconciliationReport: null,
        source: null,
        leagueId: null,
        leagueName: null,
        season: null,
        rawVersion: null,
        hashStrategy: null,
        batchId: null,
        targetCount: null,
        planningAuthorization: null,
        scheduleDetailNormalizationAuthorization: null,
        networkAuthorization: null,
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
        requestDelayMs: null,
        retry: null,
        branch: null,
        baseHead: null,
        mainHead: null,
        mainCiStatus: null,
        pr1279State: null,
        pr1279MergeCommit: null,
        acceptBaseline: false,
        acceptedBaseline: false,
        acceptIdentityMapping: false,
        identityMappingAcceptance: false,
        baselineAcceptanceAuthorization: false,
        rawWriteReadyForExecution: false,
        rawWriteRetryAuthorization: false,
        allowOddsWrite: false,
        executeWrite: false,
        commit: false,
        inventTargets: false,
        fabricateExternalIds: false,
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

function pushRequiredYes(errors, value, name) {
    if (value === true) return;
    errors.push(value === false ? `${name}=yes is required in Phase 5.21L2V3F` : `missing ${name}=yes`);
}

function pushRequiredNo(errors, value, name) {
    if (value === false) return;
    errors.push(value === true ? `${name}=yes is blocked in Phase 5.21L2V3F` : `missing ${name}=no`);
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

function readJsonFile(filePath) {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function writeJsonFile(filePath, value) {
    fs.writeFileSync(filePath, `${JSON.stringify(value, null, 4)}\n`, 'utf8');
}

function writeReportFile(filePath, value) {
    fs.writeFileSync(filePath, value, 'utf8');
}

function normalizePlanningInput(input = {}) {
    return {
        manifest: normalizeText(input.manifest),
        renewedProposal: normalizeText(input.renewedProposal),
        reportOutput: normalizeText(input.reportOutput),
        normalizationProposalOutput: normalizeText(input.normalizationProposalOutput),
        sourceInventoryReconciliationReport: normalizeText(input.sourceInventoryReconciliationReport),
        source: normalizeLower(input.source),
        leagueId: parseInteger(input.leagueId, null),
        leagueName: normalizeText(input.leagueName),
        season: normalizeText(input.season),
        rawVersion: normalizeText(input.rawVersion),
        hashStrategy: normalizeText(input.hashStrategy),
        batchId: normalizeText(input.batchId),
        targetCount: parseInteger(input.targetCount, null),
        planningAuthorization: normalizeBooleanFlag(input.planningAuthorization, undefined),
        scheduleDetailNormalizationAuthorization: normalizeBooleanFlag(
            input.scheduleDetailNormalizationAuthorization,
            undefined
        ),
        networkAuthorization: normalizeBooleanFlag(input.networkAuthorization, undefined),
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
        requestDelayMs: parseInteger(input.requestDelayMs, 0),
        retry: parseInteger(input.retry, null),
        branch: normalizeText(input.branch),
        baseHead: normalizeText(input.baseHead),
        mainHead: normalizeText(input.mainHead),
        mainCiStatus: normalizeText(input.mainCiStatus),
        pr1279State: normalizeText(input.pr1279State),
        pr1279MergeCommit: normalizeText(input.pr1279MergeCommit),
        acceptBaseline: normalizeBooleanFlag(input.acceptBaseline, false),
        acceptedBaseline: normalizeBooleanFlag(input.acceptedBaseline, false),
        acceptIdentityMapping: normalizeBooleanFlag(input.acceptIdentityMapping, false),
        identityMappingAcceptance: normalizeBooleanFlag(input.identityMappingAcceptance, false),
        baselineAcceptanceAuthorization: normalizeBooleanFlag(input.baselineAcceptanceAuthorization, false),
        rawWriteReadyForExecution: normalizeBooleanFlag(input.rawWriteReadyForExecution, false),
        rawWriteRetryAuthorization: normalizeBooleanFlag(input.rawWriteRetryAuthorization, false),
        allowOddsWrite: normalizeBooleanFlag(input.allowOddsWrite, false),
        executeWrite: normalizeBooleanFlag(input.executeWrite, false),
        commit: normalizeBooleanFlag(input.commit, false),
        inventTargets: normalizeBooleanFlag(input.inventTargets, false),
        fabricateExternalIds: normalizeBooleanFlag(input.fabricateExternalIds, false),
        unknown: Array.isArray(input.unknown) ? input.unknown : [],
    };
}

function validatePlanningInput(rawInput = {}) {
    const input = normalizePlanningInput(rawInput);
    const errors = [];

    if (input.unknown.length > 0) errors.push(`unknown arguments: ${input.unknown.join(', ')}`);
    requireExact(errors, input.manifest, MANIFEST_PATH, 'manifest');
    requireExact(errors, input.renewedProposal, RENEWED_PROPOSAL_PATH, 'renewed-proposal');
    requireExact(errors, input.reportOutput, REPORT_PATH, 'report-output');
    requireExact(
        errors,
        input.normalizationProposalOutput,
        NORMALIZATION_PROPOSAL_PATH,
        'normalization-proposal-output'
    );
    requireExact(
        errors,
        input.sourceInventoryReconciliationReport,
        SOURCE_RECONCILIATION_REPORT_PATH,
        'source-inventory-reconciliation-report'
    );
    requireExact(errors, input.source, SOURCE, 'source');
    if (input.leagueId !== LEAGUE_ID) errors.push('league-id must be 53');
    requireExact(errors, input.leagueName, LEAGUE_NAME, 'league-name');
    requireExact(errors, input.season, SEASON, 'season');
    requireExact(errors, input.rawVersion, RAW_VERSION, 'raw-version');
    requireExact(errors, input.hashStrategy, HASH_STRATEGY, 'hash-strategy');
    requireExact(errors, input.batchId, BATCH_ID, 'batch-id');
    if (input.targetCount !== TARGET_COUNT) errors.push('target-count must be 50');

    for (const key of REQUIRED_YES_FLAGS) pushRequiredYes(errors, input[key], flagName(key));
    for (const key of REQUIRED_NO_FLAGS) pushRequiredNo(errors, input[key], flagName(key));
    for (const key of BLOCKED_TRUE_FLAGS) {
        if (input[key] === true) errors.push(`${flagName(key)}=yes is blocked in Phase 5.21L2V3F`);
    }

    if (!Number.isInteger(input.requestDelayMs) || input.requestDelayMs < 0) {
        errors.push('request-delay-ms must be a non-negative integer');
    }
    if (input.retry !== 0) errors.push('retry must be 0');

    return { ok: errors.length === 0, errors, input };
}

function buildManifestGate(manifest = {}) {
    const baseGate = l2v3e.buildManifestGate(manifest);
    const errors = baseGate.errors.filter(
        error =>
            !error.startsWith(
                'manifest next_required_step must be target_identity_source_inventory_reconciliation_planning or an allowed L2V3E follow-up outcome'
            )
    );
    const nextRequiredStep = normalizeText(manifest.next_required_step);
    if (normalizeText(manifest.phase_5_21_l2v3e_planning_status) !== 'completed_no_write') {
        errors.push('manifest phase_5_21_l2v3e_planning_status must be completed_no_write');
    }
    if (!ALLOWED_L2V3E_STATUS.has(normalizeText(manifest.target_identity_source_inventory_reconciliation_status))) {
        errors.push(
            'manifest target_identity_source_inventory_reconciliation_status must be an allowed L2V3F input/output status'
        );
    }
    if (Number(manifest.phase_5_21_l2v3e_checked_target_count) !== EXPECTED_CHECKED_TARGET_COUNT) {
        errors.push(`manifest phase_5_21_l2v3e_checked_target_count must be ${EXPECTED_CHECKED_TARGET_COUNT}`);
    }
    if (Number(manifest.phase_5_21_l2v3e_identity_match_count) !== 0) {
        errors.push('manifest phase_5_21_l2v3e_identity_match_count must be 0');
    }
    if (Number(manifest.phase_5_21_l2v3e_identity_mismatch_count) !== EXPECTED_CHECKED_TARGET_COUNT) {
        errors.push(`manifest phase_5_21_l2v3e_identity_mismatch_count must be ${EXPECTED_CHECKED_TARGET_COUNT}`);
    }
    if (Number(manifest.phase_5_21_l2v3e_source_inventory_vs_manifest_mismatch_count) !== 0) {
        errors.push('manifest phase_5_21_l2v3e_source_inventory_vs_manifest_mismatch_count must be 0');
    }
    if (Number(manifest.phase_5_21_l2v3e_manifest_vs_db_mismatch_count) !== 0) {
        errors.push('manifest phase_5_21_l2v3e_manifest_vs_db_mismatch_count must be 0');
    }
    if (Number(manifest.phase_5_21_l2v3e_db_vs_live_observed_mismatch_count) !== EXPECTED_CHECKED_TARGET_COUNT) {
        errors.push(
            `manifest phase_5_21_l2v3e_db_vs_live_observed_mismatch_count must be ${EXPECTED_CHECKED_TARGET_COUNT}`
        );
    }
    if (
        Number(manifest.phase_5_21_l2v3e_requested_vs_observed_external_id_mismatch_count) !==
        EXPECTED_CHECKED_TARGET_COUNT
    ) {
        errors.push(
            `manifest phase_5_21_l2v3e_requested_vs_observed_external_id_mismatch_count must be ${EXPECTED_CHECKED_TARGET_COUNT}`
        );
    }
    if (manifest.phase_5_21_l2v3e_all_pairs_share_page_url_base !== true) {
        errors.push('manifest phase_5_21_l2v3e_all_pairs_share_page_url_base must be true');
    }
    if (normalizeText(manifest.phase_5_21_l2v3e_suspected_root_cause) !== 'schedule_vs_detail_external_id_mismatch') {
        errors.push('manifest phase_5_21_l2v3e_suspected_root_cause must be schedule_vs_detail_external_id_mismatch');
    }
    if (normalizeLower(manifest.phase_5_21_l2v3e_root_cause_confidence) !== 'high') {
        errors.push('manifest phase_5_21_l2v3e_root_cause_confidence must be high');
    }
    if (manifest.target_identity_mismatch_blocks_baseline_acceptance !== true) {
        errors.push('manifest target_identity_mismatch_blocks_baseline_acceptance must be true');
    }
    if (manifest.requires_separate_baseline_acceptance !== true) {
        errors.push('manifest requires_separate_baseline_acceptance must be true');
    }
    if (manifest.requires_separate_final_db_write_authorization !== true) {
        errors.push('manifest requires_separate_final_db_write_authorization must be true');
    }
    if (manifest.raw_write_ready_for_execution !== false) {
        errors.push('manifest raw_write_ready_for_execution must be false');
    }
    if (!ALLOWED_NEXT_STEPS.has(nextRequiredStep)) {
        errors.push('manifest next_required_step must be an allowed L2V3F input/output step');
    }
    return { ...baseGate, ok: errors.length === 0, errors };
}

function normalizeComparableDate(value) {
    const text = normalizeText(value);
    if (!text) return '';
    const date = new Date(text);
    if (Number.isNaN(date.getTime())) return text;
    return date.toISOString();
}

function normalizeTeam(value) {
    const normalized = normalizeLower(value).replace(/[^a-z0-9]/g, '');
    if (normalized === 'psg') return 'parissaintgermain';
    return normalized;
}

function unorderedTeamPairMatch(leftHome, leftAway, rightHome, rightAway) {
    const left = [normalizeTeam(leftHome), normalizeTeam(leftAway)].filter(Boolean).sort();
    const right = [normalizeTeam(rightHome), normalizeTeam(rightAway)].filter(Boolean).sort();
    if (left.length !== 2 || right.length !== 2) return false;
    return left[0] === right[0] && left[1] === right[1];
}

function teamDateStatusMatchStatus(item = {}) {
    const teamsMatch = unorderedTeamPairMatch(
        item.requested_home_team,
        item.requested_away_team,
        item.observed_home_team,
        item.observed_away_team
    );
    const dateMatch =
        normalizeComparableDate(item.requested_match_date) === normalizeComparableDate(item.observed_match_date);
    const requestedStatus = normalizeLower(item.requested_status);
    const observedStatus = normalizeLower(item.observed_status);
    const statusKnown = Boolean(requestedStatus) && Boolean(observedStatus);
    const statusMatch = statusKnown ? requestedStatus === observedStatus : null;

    if (!teamsMatch && !dateMatch && statusMatch === false) return 'team_date_status_mismatch';
    if (!teamsMatch && !dateMatch) return 'team_and_date_mismatch';
    if (!teamsMatch && statusMatch === false) return 'team_and_status_mismatch';
    if (!teamsMatch) return 'team_mismatch';
    if (teamsMatch && dateMatch && statusMatch === true) return 'compatible';
    if (teamsMatch && dateMatch && statusMatch === false) return 'status_mismatch';
    if (teamsMatch && dateMatch && statusMatch === null) return 'status_unknown';
    if (teamsMatch && !dateMatch && statusMatch === false) return 'date_and_status_mismatch';
    if (teamsMatch && !dateMatch) return 'date_mismatch';
    return 'unknown';
}

function pageUrlBaseMatchStatus(item = {}) {
    if (
        !normalizeText(item.source_inventory_page_url_base) ||
        !normalizeText(item.observed_source_inventory_page_url_base)
    ) {
        return 'missing_page_url_base';
    }
    return item.shared_page_url_base_with_observed === true ? 'match' : 'mismatch';
}

function buildMappingConflicts(items = []) {
    const scheduleToDetail = new Map();
    const detailToSchedule = new Map();

    for (const item of items) {
        const scheduleId = normalizeText(item.requested_external_id);
        const detailId = normalizeText(item.live_observed_external_id);
        if (!scheduleId || !detailId) continue;
        if (!scheduleToDetail.has(scheduleId)) scheduleToDetail.set(scheduleId, new Set());
        if (!detailToSchedule.has(detailId)) detailToSchedule.set(detailId, new Set());
        scheduleToDetail.get(scheduleId).add(detailId);
        detailToSchedule.get(detailId).add(scheduleId);
    }

    const scheduleConflicts = new Set(
        [...scheduleToDetail.entries()].filter(([, values]) => values.size > 1).map(([key]) => key)
    );
    const detailConflicts = new Set(
        [...detailToSchedule.entries()].filter(([, values]) => values.size > 1).map(([key]) => key)
    );

    return {
        schedule_conflicts: scheduleConflicts,
        detail_conflicts: detailConflicts,
        multiple_detail_ids_for_same_schedule_id_count: scheduleConflicts.size,
        multiple_schedule_ids_for_same_detail_id_count: detailConflicts.size,
    };
}

function inferProposedNormalizationKey(pageUrlStatus, compatibilityStatus, item = {}) {
    if (pageUrlStatus === 'match') return 'page_url_base';
    if (compatibilityStatus === 'compatible') return 'league+season+teams+date';
    if (normalizeText(item.source_inventory_record_key)) return 'source_inventory_record_key';
    return 'unknown';
}

function buildSafetyBlockers({ pageUrlStatus, compatibilityStatus, item = {}, conflicts = {} }) {
    const blockers = [];
    if (pageUrlStatus === 'missing_page_url_base') blockers.push('missing_page_url_base');
    if (pageUrlStatus === 'mismatch') blockers.push('page_url_base_mismatch');
    if (compatibilityStatus === 'team_mismatch') blockers.push('team_date_status_mismatch');
    if (compatibilityStatus === 'team_and_date_mismatch') blockers.push('team_date_status_mismatch');
    if (compatibilityStatus === 'team_and_status_mismatch') blockers.push('team_date_status_mismatch');
    if (compatibilityStatus === 'team_date_status_mismatch') blockers.push('team_date_status_mismatch');
    if (compatibilityStatus === 'date_mismatch') blockers.push('team_date_status_mismatch');
    if (compatibilityStatus === 'date_and_status_mismatch') blockers.push('team_date_status_mismatch');
    if (compatibilityStatus === 'status_mismatch') blockers.push('team_date_status_mismatch');
    if (compatibilityStatus === 'status_unknown') blockers.push('team_date_status_mismatch');
    if (compatibilityStatus === 'unknown') blockers.push('unknown');

    const scheduleId = normalizeText(item.requested_external_id);
    const detailId = normalizeText(item.live_observed_external_id);
    if (conflicts.schedule_conflicts?.has(scheduleId)) blockers.push('multiple_detail_ids_for_same_schedule_id');
    if (conflicts.detail_conflicts?.has(detailId)) blockers.push('multiple_schedule_ids_for_same_detail_id');
    if (!detailId) blockers.push('unknown');
    return [...new Set(blockers)];
}

function inferMappingConfidence({ pageUrlStatus, compatibilityStatus, blockers = [], item = {} }) {
    const observedDetailId =
        normalizeText(item.observed_detail_external_id) || normalizeText(item.live_observed_external_id);
    if (!observedDetailId) return 'unknown';
    if (blockers.includes('multiple_detail_ids_for_same_schedule_id')) return 'low';
    if (blockers.includes('multiple_schedule_ids_for_same_detail_id')) return 'low';
    if (pageUrlStatus === 'match' && compatibilityStatus === 'compatible') return 'high';
    if (pageUrlStatus === 'match' && compatibilityStatus === 'date_mismatch') return 'medium';
    if (pageUrlStatus === 'match' && compatibilityStatus === 'status_unknown') return 'medium';
    if (pageUrlStatus === 'match') return 'low';
    if (compatibilityStatus === 'compatible') return 'medium';
    return 'low';
}

function normalizeProposalMapping(scheduleExternalId, detailExternalId) {
    if (!scheduleExternalId || !detailExternalId) return null;
    return {
        schedule_external_id: scheduleExternalId,
        detail_external_id: detailExternalId,
    };
}

function buildNormalizationItem(baseItem = {}, conflicts = {}, observedSourceRecord = {}, generatedAt) {
    const observedStatus =
        normalizeText(baseItem.live_observed_status) || normalizeText(observedSourceRecord?.status) || null;
    const observedHomeTeam =
        normalizeText(baseItem.live_observed_home_team) || normalizeText(observedSourceRecord?.home_team) || null;
    const observedAwayTeam =
        normalizeText(baseItem.live_observed_away_team) || normalizeText(observedSourceRecord?.away_team) || null;
    const observedMatchDate =
        normalizeText(baseItem.live_observed_match_date) || normalizeText(observedSourceRecord?.match_date) || null;
    const item = {
        requested_match_id: normalizeText(baseItem.requested_match_id),
        requested_schedule_external_id: normalizeText(baseItem.requested_external_id),
        requested_league: normalizeText(baseItem.requested_league),
        requested_season: normalizeText(baseItem.requested_season),
        requested_home_team: normalizeText(baseItem.requested_home_team),
        requested_away_team: normalizeText(baseItem.requested_away_team),
        requested_match_date: normalizeText(baseItem.requested_match_date),
        requested_status: normalizeText(baseItem.requested_status),
        source_inventory_path: normalizeText(baseItem.source_inventory_path) || null,
        source_inventory_record_key: normalizeText(baseItem.source_inventory_record_key) || null,
        source_inventory_page_url_base: normalizeText(baseItem.source_inventory_page_url_base) || null,
        manifest_page_url_base: normalizeText(baseItem.manifest_page_url_base) || null,
        live_observed_page_url_base:
            normalizeText(baseItem.observed_source_inventory_page_url_base) ||
            normalizeText(baseItem.live_observed_page_url_base) ||
            null,
        observed_detail_external_id: normalizeText(baseItem.live_observed_external_id) || null,
        observed_home_team: observedHomeTeam,
        observed_away_team: observedAwayTeam,
        observed_match_date: observedMatchDate,
        observed_status: observedStatus,
        mapping_source: 'source_inventory_page_url_base_plus_prior_safe_live_metadata',
        mapping_verified_at: generatedAt,
    };
    item.page_url_base_match_status = pageUrlBaseMatchStatus(baseItem);
    item.team_date_status_match_status = teamDateStatusMatchStatus(item);
    item.schedule_external_id_vs_detail_external_id_status =
        item.requested_schedule_external_id && item.observed_detail_external_id
            ? item.requested_schedule_external_id === item.observed_detail_external_id
                ? 'same'
                : 'different'
            : 'unknown';
    item.proposed_normalization_key = inferProposedNormalizationKey(
        item.page_url_base_match_status,
        item.team_date_status_match_status,
        baseItem
    );
    item.safety_blockers = buildSafetyBlockers({
        pageUrlStatus: item.page_url_base_match_status,
        compatibilityStatus: item.team_date_status_match_status,
        item: baseItem,
        conflicts,
    });
    item.mapping_confidence = inferMappingConfidence({
        pageUrlStatus: item.page_url_base_match_status,
        compatibilityStatus: item.team_date_status_match_status,
        blockers: item.safety_blockers,
        item,
    });
    item.proposed_mapping = normalizeProposalMapping(
        item.requested_schedule_external_id,
        item.observed_detail_external_id
    );
    item.mapping_status =
        item.mapping_confidence === 'high' && item.safety_blockers.length === 0
            ? 'proposal_only_high_confidence_unaccepted'
            : item.proposed_mapping
              ? 'proposal_only_unaccepted'
              : 'unresolved_unknown';
    return item;
}

function countBy(values = []) {
    return values.reduce((acc, value) => {
        const key = normalizeText(value) || 'unknown';
        acc[key] = (acc[key] || 0) + 1;
        return acc;
    }, {});
}

function inferRecommendedNextStep(summary = {}) {
    if (
        summary.checked_target_count > 0 &&
        summary.high_confidence_mapping_count === summary.checked_target_count &&
        summary.unresolved_mapping_count === 0
    ) {
        return 'schedule_detail_identity_mapping_acceptance_review';
    }
    if (summary.route_fix_planning_required === true) {
        return 'schedule_detail_route_normalization_fix_implementation_planning';
    }
    if (summary.proposed_mapping_count > 0 && summary.checked_target_count < summary.candidate_targets_count) {
        return 'expanded no-write schedule detail normalization proposal';
    }
    return 'continued target identity investigation';
}

function buildSummary({
    input = {},
    manifestGate = {},
    l2v3eResult = {},
    items = [],
    conflicts = {},
    generatedAt,
} = {}) {
    const proposedMappingCount = items.filter(item => item.proposed_mapping).length;
    const highConfidenceCount = items.filter(item => item.mapping_confidence === 'high').length;
    const mediumConfidenceCount = items.filter(item => item.mapping_confidence === 'medium').length;
    const lowConfidenceCount = items.filter(item => item.mapping_confidence === 'low').length;
    const unresolvedMappingCount = items.filter(item => item.safety_blockers.length > 0).length;
    const pageUrlBaseMatchCount = items.filter(item => item.page_url_base_match_status === 'match').length;
    const teamDateStatusCompatibleCount = items.filter(
        item => item.team_date_status_match_status === 'compatible'
    ).length;
    const teamDateStatusMismatchCount = items.filter(
        item => item.team_date_status_match_status !== 'compatible'
    ).length;
    const teamPairMatchCount = items.filter(item =>
        unorderedTeamPairMatch(
            item.requested_home_team,
            item.requested_away_team,
            item.observed_home_team,
            item.observed_away_team
        )
    ).length;
    const exactDateMatchCount = items.filter(
        item => normalizeComparableDate(item.requested_match_date) === normalizeComparableDate(item.observed_match_date)
    ).length;
    const routeFixPlanningRequired =
        items.length > 0 &&
        pageUrlBaseMatchCount === items.length &&
        teamPairMatchCount === items.length &&
        exactDateMatchCount === 0 &&
        highConfidenceCount === 0;

    const summary = {
        phase: PHASE,
        generated_at: generatedAt,
        source_manifest_path: input.manifest,
        renewed_baseline_proposal_path: input.renewedProposal,
        source_inventory_reconciliation_report: input.sourceInventoryReconciliationReport,
        normalization_proposal_path: input.normalizationProposalOutput,
        report_path: input.reportOutput,
        branch: input.branch || null,
        base_head: input.baseHead || null,
        main_head: input.mainHead || null,
        main_ci_status: input.mainCiStatus || null,
        pr_1279_state: input.pr1279State || null,
        pr_1279_merge_commit: input.pr1279MergeCommit || null,
        no_write: true,
        db_write_performed: false,
        raw_insert_performed: false,
        baseline_acceptance_performed: false,
        identity_mapping_acceptance_performed: false,
        raw_write_retry_performed: false,
        checked_target_count: items.length,
        candidate_targets_count: manifestGate.candidate_targets_count || 0,
        proposed_mapping_count: proposedMappingCount,
        high_confidence_mapping_count: highConfidenceCount,
        medium_confidence_mapping_count: mediumConfidenceCount,
        low_confidence_mapping_count: lowConfidenceCount,
        unresolved_mapping_count: unresolvedMappingCount,
        page_url_base_match_count: pageUrlBaseMatchCount,
        team_pair_match_count: teamPairMatchCount,
        exact_date_match_count: exactDateMatchCount,
        team_date_status_compatible_count: teamDateStatusCompatibleCount,
        team_date_status_mismatch_count: teamDateStatusMismatchCount,
        page_url_base_match_status_counts: countBy(items.map(item => item.page_url_base_match_status)),
        team_date_status_match_status_counts: countBy(items.map(item => item.team_date_status_match_status)),
        mapping_confidence_counts: countBy(items.map(item => item.mapping_confidence)),
        mapping_status_counts: countBy(items.map(item => item.mapping_status)),
        multiple_detail_ids_for_same_schedule_id_count: conflicts.multiple_detail_ids_for_same_schedule_id_count || 0,
        multiple_schedule_ids_for_same_detail_id_count: conflicts.multiple_schedule_ids_for_same_detail_id_count || 0,
        raw_write_ready_for_execution: false,
        target_identity_mismatch_blocks_baseline_acceptance: true,
        schedule_detail_normalization_required: true,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        l2v3e_suspected_root_cause: l2v3eResult.summary?.suspected_root_cause || null,
        l2v3e_root_cause_confidence: l2v3eResult.summary?.root_cause_confidence || null,
        route_fix_planning_required: routeFixPlanningRequired,
        db_row_counts: l2v3eResult.summary?.db_row_counts || {},
        candidate_v2_rows_count: Number(l2v3eResult.summary?.candidate_v2_rows_count || 0),
    };
    summary.recommended_next_step = inferRecommendedNextStep(summary);
    return summary;
}

function buildUpdatedManifest(manifest = {}, summary = {}) {
    return {
        ...manifest,
        phase_5_21_l2v3f_planning_status: 'completed_no_write',
        schedule_detail_identity_normalization_status:
            summary.recommended_next_step === 'schedule_detail_route_normalization_fix_implementation_planning'
                ? 'blocked_pending_route_normalization_fix_planning_required'
                : summary.recommended_next_step === 'expanded no-write schedule detail normalization proposal'
                  ? 'blocked_pending_expanded_normalization_proposal'
                  : summary.recommended_next_step === 'schedule_detail_identity_mapping_acceptance_review'
                    ? 'proposal_only_ready_for_identity_mapping_acceptance_review'
                    : 'blocked_pending_schedule_detail_investigation',
        phase_5_21_l2v3f_checked_target_count: summary.checked_target_count,
        phase_5_21_l2v3f_proposed_mapping_count: summary.proposed_mapping_count,
        phase_5_21_l2v3f_high_confidence_mapping_count: summary.high_confidence_mapping_count,
        phase_5_21_l2v3f_medium_confidence_mapping_count: summary.medium_confidence_mapping_count,
        phase_5_21_l2v3f_low_confidence_mapping_count: summary.low_confidence_mapping_count,
        phase_5_21_l2v3f_unresolved_mapping_count: summary.unresolved_mapping_count,
        phase_5_21_l2v3f_page_url_base_match_count: summary.page_url_base_match_count,
        phase_5_21_l2v3f_team_pair_match_count: summary.team_pair_match_count,
        phase_5_21_l2v3f_exact_date_match_count: summary.exact_date_match_count,
        phase_5_21_l2v3f_team_date_status_compatible_count: summary.team_date_status_compatible_count,
        phase_5_21_l2v3f_team_date_status_mismatch_count: summary.team_date_status_mismatch_count,
        phase_5_21_l2v3f_page_url_base_match_status_counts: summary.page_url_base_match_status_counts,
        phase_5_21_l2v3f_team_date_status_match_status_counts: summary.team_date_status_match_status_counts,
        phase_5_21_l2v3f_mapping_confidence_counts: summary.mapping_confidence_counts,
        phase_5_21_l2v3f_mapping_status_counts: summary.mapping_status_counts,
        phase_5_21_l2v3f_multiple_detail_ids_for_same_schedule_id_count:
            summary.multiple_detail_ids_for_same_schedule_id_count,
        phase_5_21_l2v3f_multiple_schedule_ids_for_same_detail_id_count:
            summary.multiple_schedule_ids_for_same_detail_id_count,
        phase_5_21_l2v3f_normalization_proposal_path: summary.normalization_proposal_path,
        raw_write_ready_for_execution: false,
        target_identity_mismatch_blocks_baseline_acceptance: true,
        schedule_detail_normalization_required: true,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        next_required_step: summary.recommended_next_step,
    };
}

function buildNormalizationProposal({ manifestGate = {}, items = [], summary = {}, input = {} }) {
    const checkedByExternalId = new Map(items.map(item => [item.requested_schedule_external_id, item]));
    const uncheckedTargets = (manifestGate.candidates || [])
        .filter(target => !checkedByExternalId.has(normalizeText(target.external_id)))
        .map(target => ({
            requested_schedule_external_id: normalizeText(target.external_id),
            requested_match_id: normalizeText(target.match_id),
            mapping_status: 'not_evaluated_in_l2v3f',
        }));
    return {
        proposal_phase: 'Phase 5.21L2V3F',
        proposal_status: 'schedule_detail_identity_normalization_review_required',
        no_write: true,
        db_write_performed: false,
        raw_insert_performed: false,
        baseline_acceptance_performed: false,
        identity_mapping_acceptance_performed: false,
        raw_write_ready_for_execution: false,
        source_manifest_path: input.manifest,
        source_inventory_reconciliation_report: input.sourceInventoryReconciliationReport,
        candidate_targets_count: summary.candidate_targets_count,
        checked_targets_count: summary.checked_target_count,
        proposed_mapping_count: summary.proposed_mapping_count,
        high_confidence_mapping_count: summary.high_confidence_mapping_count,
        medium_confidence_mapping_count: summary.medium_confidence_mapping_count,
        low_confidence_mapping_count: summary.low_confidence_mapping_count,
        unresolved_mapping_count: summary.unresolved_mapping_count,
        mapping_strategy: {
            primary_anchor: 'page_url_base',
            fallback_anchor: 'league+season+teams+date',
            acceptance_rule:
                'page_url_base match plus team/date/status compatibility only; proposal-only mapping stays blocked until separate identity mapping acceptance',
        },
        requires_human_review: true,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        checked_targets: items.map(item => ({
            requested_schedule_external_id: item.requested_schedule_external_id,
            requested_match_id: item.requested_match_id,
            observed_detail_external_id: item.observed_detail_external_id,
            page_url_base_match_status: item.page_url_base_match_status,
            team_date_status_match_status: item.team_date_status_match_status,
            mapping_confidence: item.mapping_confidence,
            mapping_status: item.mapping_status,
            proposed_mapping: item.proposed_mapping,
            safety_blockers: item.safety_blockers,
        })),
        unchecked_targets: uncheckedTargets,
        targets_not_checked: uncheckedTargets,
        normalized_identity_model: {
            schedule_external_id: 'separate',
            detail_external_id: 'separate',
            page_url_base: 'proposal_only_anchor',
            league_id: LEAGUE_ID,
            season: SEASON,
            home_team: 'proposal_only',
            away_team: 'proposal_only',
            match_date: 'proposal_only',
            status: 'proposal_only',
            mapping_confidence: 'proposal_only',
            mapping_source: 'source_inventory_page_url_base_plus_prior_safe_live_metadata',
            mapping_verified_at: summary.generated_at,
        },
        recommended_next_step: summary.recommended_next_step,
    };
}

function buildMappingRows(items = []) {
    return items.map(
        item =>
            `| ${item.requested_match_id} | ${item.requested_schedule_external_id} | ${item.requested_home_team}-${item.requested_away_team} | ${item.requested_match_date} | ${item.requested_status} | ${item.source_inventory_page_url_base || ''} | ${item.manifest_page_url_base || ''} | ${item.live_observed_page_url_base || ''} | ${item.observed_detail_external_id || ''} | ${item.observed_home_team || ''}-${item.observed_away_team || ''} | ${item.observed_match_date || ''} | ${item.observed_status || ''} | ${item.page_url_base_match_status} | ${item.team_date_status_match_status} | ${item.schedule_external_id_vs_detail_external_id_status} | ${item.proposed_normalization_key} | ${item.mapping_confidence} | ${(item.safety_blockers || []).join(',')} |`
    );
}

function buildReport({ summary = {}, items = [], proposal = {} } = {}) {
    const rows = buildMappingRows(items);
    return `# Data Entrypoint Governance - Phase 5.21 L2V3F

## A. Current Status

- phase=schedule detail identity normalization fix planning
- branch=${summary.branch || 'unknown'}
- base_head=${summary.base_head || 'unknown'}
- main_head=${summary.main_head || 'unknown'}
- main_ci_status=${summary.main_ci_status || 'unknown'}
- source_manifest_path=${summary.source_manifest_path}
- renewed_baseline_proposal_path=${summary.renewed_baseline_proposal_path}
- source_inventory_reconciliation_report=${summary.source_inventory_reconciliation_report}
- normalization_proposal_path=${summary.normalization_proposal_path}
- report_path=${summary.report_path}

## B. PR #1279 Merge Result

- pr_1279_state=${summary.pr_1279_state || 'unknown'}
- pr_1279_merge_commit=${summary.pr_1279_merge_commit || 'unknown'}
- merge_scope=L2V3E no-write source inventory reconciliation planning

## C. main HEAD / CI Status

- main_head=${summary.main_head || 'unknown'}
- main_ci_status=${summary.main_ci_status || 'unknown'}

## D. Authorization Scope

- planning_authorized=true
- schedule_detail_normalization_authorized=true
- network_authorized_for_source_inventory_only=true
- no match detail live check executed in L2V3F
- no accepted identity mapping
- no accepted baseline replacement
- no raw write authorization

## E. No-Write Guarantee

- db_write_performed=false
- raw_insert_performed=false
- identity_mapping_acceptance_performed=false
- baseline_acceptance_performed=false
- raw_write_retry_performed=false
- full raw_data/pageProps/source body printed=false
- full raw_data/pageProps/source body saved=false

## F. L2V3E Root Cause Recap

- l2v3e_suspected_root_cause=${summary.l2v3e_suspected_root_cause || 'unknown'}
- l2v3e_root_cause_confidence=${summary.l2v3e_root_cause_confidence || 'unknown'}
- checked_target_count=${summary.checked_target_count}
- proposed_mapping_count=${summary.proposed_mapping_count}
- high_confidence_mapping_count=${summary.high_confidence_mapping_count}
- unresolved_mapping_count=${summary.unresolved_mapping_count}

## G. Schedule / Listing Vs Detail Identity Evidence

- requested_vs_observed_external_id_behavior=distinct_identity_surfaces_observed
- page_url_base_match_count=${summary.page_url_base_match_count}
- team_pair_match_count=${summary.team_pair_match_count}
- exact_date_match_count=${summary.exact_date_match_count}
- team_date_status_compatible_count=${summary.team_date_status_compatible_count}
- team_date_status_mismatch_count=${summary.team_date_status_mismatch_count}
- multiple_detail_ids_for_same_schedule_id_count=${summary.multiple_detail_ids_for_same_schedule_id_count}
- multiple_schedule_ids_for_same_detail_id_count=${summary.multiple_schedule_ids_for_same_detail_id_count}

## H. PageUrl Base Normalization Analysis

- primary_anchor=page_url_base
- page_url_base_match_status_counts=${JSON.stringify(summary.page_url_base_match_status_counts)}
- team_date_status_match_status_counts=${JSON.stringify(summary.team_date_status_match_status_counts)}
- page_url_base_is_candidate_anchor_only=true
- high_confidence_requires_page_url_base_plus_team_date_status_compatibility=true

## I. 8 Mismatch Target Safe Mapping Summary

| requested_match_id | requested_schedule_external_id | requested_teams | requested_match_date | requested_status | source_inventory_page_url_base | manifest_page_url_base | live_observed_page_url_base | observed_detail_external_id | observed_teams | observed_match_date | observed_status | page_url_base_match_status | team_date_status_match_status | schedule_external_id_vs_detail_external_id_status | proposed_normalization_key | mapping_confidence | safety_blockers |
| ------------------ | ------------------------------ | --------------- | -------------------- | ---------------- | ------------------------------ | ---------------------- | --------------------------- | --------------------------- | -------------- | ------------------- | --------------- | -------------------------- | ----------------------------- | ------------------------------------------------- | -------------------------- | ------------------ | --------------- |
${rows.join('\n')}

## J. Proposed Normalization Model

- normalized_identity_model=${JSON.stringify(proposal.normalized_identity_model || {}, null, 2)}

## K. Proposed Gating Rules

- raw_write_ready_for_execution=false unless separate identity mapping acceptance completes
- proposal_only_mapping_never_usable_by_raw_write_runner=true
- unresolved_or_unaccepted_normalization_blocks_baseline_acceptance=true
- unresolved_or_unaccepted_normalization_blocks_raw_write_retry=true
- requires_separate_identity_mapping_acceptance=true
- requires_separate_baseline_acceptance=true
- requires_separate_final_db_write_authorization=true

## L. Required Fix / Continue Investigation Decision

- code_fix_required=${summary.route_fix_planning_required === true}
- manifest_regeneration_required=false
- identity_mapping_acceptance_required=true
- continue_investigation_required=${summary.recommended_next_step === 'continued target identity investigation'}
- recommended_next_step=${summary.recommended_next_step}

## M. Normalization Proposal File Path

- normalization_proposal_path=${summary.normalization_proposal_path}

## N. DB Row Count Safety Result

- matches=${summary.db_row_counts.matches ?? 'unknown'}
- raw_match_data=${summary.db_row_counts.raw_match_data ?? 'unknown'}
- bookmaker_odds_history=${summary.db_row_counts.bookmaker_odds_history ?? 'unknown'}
- l3_features=${summary.db_row_counts.l3_features ?? 'unknown'}
- match_features_training=${summary.db_row_counts.match_features_training ?? 'unknown'}
- predictions=${summary.db_row_counts.predictions ?? 'unknown'}
- candidate_v2_rows_count=${summary.candidate_v2_rows_count}
- expected_matches=${EXPECTED_ROW_COUNTS.matches}
- expected_raw_match_data=${EXPECTED_ROW_COUNTS.raw_match_data}

## O. Test Results

- pending until local verification completes

## P. PR Status

- pending until PR is created

## Q. Next Step Recommendation

- recommended_next_step=${summary.recommended_next_step}
- unresolved or unaccepted normalization blocks baseline acceptance.
- unresolved or unaccepted normalization blocks raw write retry.

## R. Explicit Non-Execution

- no DB writes
- no raw_match_data inserts
- no matches writes
- no bookmaker_odds_history writes
- no l3_features writes
- no match_features_training writes
- no predictions writes
- no schema migration
- no parser implementation for production execution
- no feature extraction
- no training/prediction
- no browser/proxy/captcha bypass
- no accepted identity mapping
- no accepted baseline replacement
- no raw write retry
- no proposal hash marked as accepted baseline
- no full raw_data/pageProps/source body print/save
- no invented external_id, target, payload, or hash
- no matches.external_id modification
`;
}

function sleep(ms) {
    if (!ms) return Promise.resolve();
    return new Promise(resolve => {
        setTimeout(resolve, ms);
    });
}

async function runPlanning(rawInput = {}, dependencies = {}) {
    const validation = validatePlanningInput(rawInput);
    if (!validation.ok) return { ok: false, status: 2, errors: validation.errors };
    const input = validation.input;
    const generatedAt = dependencies.generatedAt || new Date().toISOString();
    const manifest = dependencies.manifest || (dependencies.readJsonFile || readJsonFile)(input.manifest);
    const manifestGate = buildManifestGate(manifest);
    if (!manifestGate.ok) return { ok: false, status: 3, errors: manifestGate.errors, manifest_gate: manifestGate };
    const l2v3eReplayManifest = {
        ...manifest,
        next_required_step: 'schedule_detail_identity_normalization_fix_planning',
    };

    const l2v3eResult = await l2v3e.runPlanning(
        {
            manifest: input.manifest,
            renewedProposal: input.renewedProposal,
            reportOutput: l2v3e.REPORT_PATH,
            source: input.source,
            leagueId: input.leagueId,
            leagueName: input.leagueName,
            season: input.season,
            rawVersion: input.rawVersion,
            hashStrategy: input.hashStrategy,
            batchId: input.batchId,
            targetCount: input.targetCount,
            planningAuthorization: true,
            sourceInventoryReconciliationAuthorization: true,
            networkAuthorization: input.networkAuthorization,
            allowDbWrite: false,
            allowRawMatchDataWrite: false,
            allowControlledWrite: false,
            allowMatchesWrite: false,
            allowBookmakerOddsWrite: false,
            allowFeatureWrite: false,
            allowSchemaMigration: false,
            allowParserImplementation: false,
            allowFeatureExtraction: false,
            allowTraining: false,
            allowPrediction: false,
            allowBrowserRuntime: false,
            allowProxyRuntime: false,
            printFullBody: false,
            saveFullBody: false,
            printFullJson: false,
            saveFullJson: false,
            printFullPageprops: false,
            saveFullPageprops: false,
            retry: 0,
            requestDelayMs: input.requestDelayMs,
            branch: input.branch,
            baseHead: input.baseHead,
            mainHead: input.mainHead,
            mainCiStatus: input.mainCiStatus,
            pr1278State: 'MERGED',
            pr1278MergeCommit: normalizeText(manifest.phase_5_21_l2v3e_prerequisite_merge_commit),
        },
        {
            ...dependencies,
            manifest: l2v3eReplayManifest,
            writeManifest: false,
            writeReport: false,
            generatedAt,
        }
    );

    if (!l2v3eResult.ok) {
        return {
            ok: false,
            status: 4,
            errors: l2v3eResult.errors || ['L2V3E prerequisite replay failed'],
            l2v3e_result: l2v3eResult,
        };
    }

    const sourceByExternalId = new Map(
        Object.entries(l2v3eResult.source_inventory_selection?.selected_by_external_id || {})
    );
    const conflicts = buildMappingConflicts(l2v3eResult.items || []);
    const items = (l2v3eResult.items || []).map(item =>
        buildNormalizationItem(
            item,
            conflicts,
            sourceByExternalId.get(normalizeText(item.live_observed_external_id)),
            generatedAt
        )
    );
    const summary = buildSummary({
        input,
        manifestGate,
        l2v3eResult,
        items,
        conflicts,
        generatedAt,
    });
    const updatedManifest = buildUpdatedManifest(manifest, summary);
    const proposal = buildNormalizationProposal({
        manifestGate,
        items,
        summary,
        input,
    });
    const report = buildReport({ summary, items, proposal });

    if (dependencies.writeManifest !== false) {
        (dependencies.writeManifestFile || dependencies.writeJsonFile || writeJsonFile)(
            input.manifest,
            updatedManifest
        );
    }
    if (dependencies.writeProposal !== false) {
        (dependencies.writeProposalFile || dependencies.writeJsonFile || writeJsonFile)(
            input.normalizationProposalOutput,
            proposal
        );
    }
    if (dependencies.writeReport !== false) {
        (dependencies.writeReportFile || writeReportFile)(input.reportOutput, report);
    }

    return {
        ok: true,
        status: 0,
        summary,
        items,
        proposal,
        updated_manifest: updatedManifest,
        report,
        manifest_gate: manifestGate,
        l2v3e_result: l2v3eResult,
        conflicts,
    };
}

async function runCli(argv = process.argv.slice(2), dependencies = {}) {
    const args = parseArgs(argv);
    if (args.help) {
        process.stdout.write(
            `Usage: node scripts/ops/pageprops_v2_schedule_detail_identity_normalization_plan.js --manifest=${MANIFEST_PATH} --renewed-proposal=${RENEWED_PROPOSAL_PATH} --report-output=${REPORT_PATH} --normalization-proposal-output=${NORMALIZATION_PROPOSAL_PATH} ...\n`
        );
        return { status: 0 };
    }
    const result = await runPlanning(args, dependencies);
    const output = result.ok
        ? {
              ok: true,
              status: result.status,
              summary: result.summary,
          }
        : {
              ok: false,
              status: result.status,
              errors: result.errors,
          };
    process.stdout.write(`${JSON.stringify(output, null, 2)}\n`);
    return { status: result.status };
}

module.exports = {
    PHASE,
    MANIFEST_PATH,
    RENEWED_PROPOSAL_PATH,
    REPORT_PATH,
    NORMALIZATION_PROPOSAL_PATH,
    SOURCE_RECONCILIATION_REPORT_PATH,
    SOURCE,
    LEAGUE_ID,
    LEAGUE_NAME,
    SEASON,
    RAW_VERSION,
    HASH_STRATEGY,
    BATCH_ID,
    TARGET_COUNT,
    EXPECTED_CHECKED_TARGET_COUNT,
    EXPECTED_ROW_COUNTS,
    parseArgs,
    normalizeBooleanFlag,
    readJsonFile,
    writeJsonFile,
    writeReportFile,
    validatePlanningInput,
    buildManifestGate,
    teamDateStatusMatchStatus,
    pageUrlBaseMatchStatus,
    buildMappingConflicts,
    buildNormalizationItem,
    buildSummary,
    buildUpdatedManifest,
    buildNormalizationProposal,
    buildReport,
    sleep,
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
