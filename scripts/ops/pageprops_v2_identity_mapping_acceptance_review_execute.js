#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const adPlan = require('./pageprops_v2_identity_mapping_acceptance_review_plan');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3AE';
const PHASE_NAME = 'identity_mapping_acceptance_review_execution';
const ARTIFACT_STATUS = 'completed_identity_mapping_acceptance_review_execution';
const BLOCKED_STATUS = 'blocked_identity_mapping_acceptance_review_execution';
const GENERATED_AT = '2026-05-22T10:30:00Z';
const DEFAULT_ACCEPTED_BY = 'codex_automation_on_user_authorization';
const MANIFEST_PATH = adPlan.MANIFEST_PATH;
const L2V3AD_PLAN_PATH = adPlan.ARTIFACT_OUTPUT_PATH;
const L2V3AC_ARTIFACT_PATH = adPlan.L2V3AC_ARTIFACT_PATH;
const L2V3AA_ARTIFACT_PATH = adPlan.L2V3AA_ARTIFACT_PATH;
const L2V3Y_ARTIFACT_PATH = adPlan.L2V3Y_ARTIFACT_PATH;
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.identity_mapping_acceptance_result.phase521l2v3ae.json';
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AE.md';
const EXPECTED_TARGET_COUNT = 50;
const ACCEPTED_NEXT_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AF: baseline acceptance planning',
    next_required_step: 'baseline_acceptance_planning',
});
const BLOCKED_NEXT_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AF: identity mapping acceptance blocker resolution',
    next_required_step: 'identity_mapping_acceptance_blocker_resolution',
});
const CONTINUED_PLANNING_NEXT_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AF: continued identity mapping acceptance review planning',
    next_required_step: 'continued_identity_mapping_acceptance_review_planning',
});
const BLOCKED_TRUE_FLAGS = Object.freeze([
    'allowDbWrite',
    'allowNetwork',
    'allowLiveFetch',
    'allowDetailFetch',
    'allowRawMatchDataWrite',
    'allowMatchesWrite',
    'allowMatchesExternalIdWrite',
    'allowSchemaMigration',
    'allowParserImplementation',
    'allowFeatureExtraction',
    'allowTraining',
    'allowPrediction',
    'allowBrowserRuntime',
    'allowProxyRuntime',
    'acceptBaseline',
    'allowRawWriteRetry',
    'executeRawWrite',
    'printFullBody',
    'saveFullBody',
    'printFullJson',
    'saveFullJson',
    'printFullPageprops',
    'saveFullPageprops',
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

function normalizeBooleanFlag(value, fallback = false) {
    if (typeof value === 'boolean') return value;
    if (value === null || value === undefined || value === '') return fallback;
    const normalized = normalizeText(value).toLowerCase();
    if (['1', 'true', 'yes', 'y', 'on'].includes(normalized)) return true;
    if (['0', 'false', 'no', 'n', 'off'].includes(normalized)) return false;
    return fallback;
}

function parseOptionValue(arg, argv, index) {
    if (arg.includes('=')) return { value: arg.slice(arg.indexOf('=') + 1), consumedNext: false };
    const nextArg = argv[index + 1];
    if (typeof nextArg === 'string' && !nextArg.startsWith('--')) return { value: nextArg, consumedNext: true };
    return { value: true, consumedNext: false };
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = {
        writeFiles: true,
        humanReviewSatisfied: false,
        acceptedBy: DEFAULT_ACCEPTED_BY,
        acceptedAt: GENERATED_AT,
        help: false,
        unknown: [],
    };
    const keyMap = {
        'write-files': 'writeFiles',
        write_files: 'writeFiles',
        'human-review-satisfied': 'humanReviewSatisfied',
        human_review_satisfied: 'humanReviewSatisfied',
        'accepted-by': 'acceptedBy',
        accepted_by: 'acceptedBy',
        'accepted-at': 'acceptedAt',
        accepted_at: 'acceptedAt',
        'allow-db-write': 'allowDbWrite',
        allow_db_write: 'allowDbWrite',
        'allow-network': 'allowNetwork',
        allow_network: 'allowNetwork',
        'allow-live-fetch': 'allowLiveFetch',
        allow_live_fetch: 'allowLiveFetch',
        'allow-detail-fetch': 'allowDetailFetch',
        allow_detail_fetch: 'allowDetailFetch',
        'allow-raw-match-data-write': 'allowRawMatchDataWrite',
        allow_raw_match_data_write: 'allowRawMatchDataWrite',
        'allow-matches-write': 'allowMatchesWrite',
        allow_matches_write: 'allowMatchesWrite',
        'allow-matches-external-id-write': 'allowMatchesExternalIdWrite',
        allow_matches_external_id_write: 'allowMatchesExternalIdWrite',
        'allow-schema-migration': 'allowSchemaMigration',
        allow_schema_migration: 'allowSchemaMigration',
        'allow-parser-implementation': 'allowParserImplementation',
        allow_parser_implementation: 'allowParserImplementation',
        'allow-feature-extraction': 'allowFeatureExtraction',
        allow_feature_extraction: 'allowFeatureExtraction',
        'allow-training': 'allowTraining',
        allow_training: 'allowTraining',
        'allow-prediction': 'allowPrediction',
        allow_prediction: 'allowPrediction',
        'allow-browser-runtime': 'allowBrowserRuntime',
        allow_browser_runtime: 'allowBrowserRuntime',
        'allow-proxy-runtime': 'allowProxyRuntime',
        allow_proxy_runtime: 'allowProxyRuntime',
        'accept-baseline': 'acceptBaseline',
        accept_baseline: 'acceptBaseline',
        'allow-raw-write-retry': 'allowRawWriteRetry',
        allow_raw_write_retry: 'allowRawWriteRetry',
        'execute-raw-write': 'executeRawWrite',
        execute_raw_write: 'executeRawWrite',
        'print-full-body': 'printFullBody',
        print_full_body: 'printFullBody',
        'save-full-body': 'saveFullBody',
        save_full_body: 'saveFullBody',
        'print-full-json': 'printFullJson',
        print_full_json: 'printFullJson',
        'save-full-json': 'saveFullJson',
        save_full_json: 'saveFullJson',
        'print-full-pageprops': 'printFullPageprops',
        print_full_pageprops: 'printFullPageprops',
        'save-full-pageprops': 'saveFullPageprops',
        save_full_pageprops: 'saveFullPageprops',
        help: 'help',
        h: 'help',
    };
    const booleanKeys = new Set(['writeFiles', 'humanReviewSatisfied', 'help', ...BLOCKED_TRUE_FLAGS]);

    for (let index = 0; index < argv.length; index += 1) {
        const arg = String(argv[index]);
        if (!arg.startsWith('--')) {
            options.unknown.push(arg);
            continue;
        }
        const rawKey = arg.replace(/^--/, '').split('=')[0];
        const optionKey = keyMap[rawKey];
        const { value, consumedNext } = parseOptionValue(arg, argv, index);
        if (consumedNext) index += 1;
        if (!optionKey) {
            options.unknown.push(rawKey);
            continue;
        }
        options[optionKey] = booleanKeys.has(optionKey) ? normalizeBooleanFlag(value, true) : value;
    }
    return options;
}

function cliName(flagName) {
    return flagName.replace(/[A-Z]/g, character => `-${character.toLowerCase()}`);
}

function validateCliOptions(options = {}) {
    const errors = [];
    if (Array.isArray(options.unknown) && options.unknown.length > 0) {
        errors.push(`unknown arguments: ${options.unknown.join(', ')}`);
    }
    for (const flagName of BLOCKED_TRUE_FLAGS) {
        if (normalizeBooleanFlag(options[flagName], false) === true) {
            errors.push(`${cliName(flagName)}=yes is blocked`);
        }
    }
    if (normalizeBooleanFlag(options.humanReviewSatisfied, false) === true) {
        if (!normalizeText(options.acceptedBy)) errors.push('accepted-by is required when human-review-satisfied=yes');
        if (!normalizeText(options.acceptedAt)) errors.push('accepted-at is required when human-review-satisfied=yes');
    }
    return { ok: errors.length === 0, errors };
}

function countBy(values = []) {
    const counts = new Map();
    for (const value of values.map(item => normalizeText(item)).filter(Boolean)) {
        counts.set(value, (counts.get(value) || 0) + 1);
    }
    return counts;
}

function indexBy(values = [], keyName) {
    const map = new Map();
    for (const value of values) {
        const key = normalizeText(value?.[keyName]);
        if (key) map.set(key, value);
    }
    return map;
}

function isDuplicate(counts, value) {
    const key = normalizeText(value);
    return Boolean(key && (counts.get(key) || 0) > 1);
}

function hasUnsafeWriteState(value = {}) {
    return (
        value.baseline_acceptance_performed === true ||
        value.raw_write_retry_performed === true ||
        value.raw_write_ready_for_execution === true ||
        value.db_write_performed === true ||
        value.raw_match_data_insert_performed === true ||
        value.matches_write_performed === true ||
        value.matches_external_id_modified === true
    );
}

function validateInputs(
    manifest = {},
    planArtifact = {},
    l2v3acArtifact = {},
    l2v3aaArtifact = {},
    l2v3yArtifact = {}
) {
    const errors = [];
    const alreadyExecuted =
        normalizeText(manifest.phase_5_21_l2v3ae_execution_status) ===
            'completed_identity_mapping_acceptance_review_execution' &&
        normalizeText(manifest.next_required_step) === 'baseline_acceptance_planning';
    if (
        normalizeText(manifest.next_required_step) !== 'identity_mapping_acceptance_review_execution' &&
        alreadyExecuted !== true
    ) {
        errors.push('manifest next_required_step must be identity_mapping_acceptance_review_execution');
    }
    if (Number(manifest.accepted_mapping_count || 0) !== 0) {
        errors.push('manifest accepted_mapping_count must be 0 before L2V3AE execution');
    }
    if (manifest.identity_mapping_acceptance_performed === true) {
        errors.push('manifest identity_mapping_acceptance_performed must be false before L2V3AE execution');
    }
    if (hasUnsafeWriteState(manifest)) {
        errors.push('manifest must not contain write-ready, DB-write, baseline, or raw retry state');
    }

    if (planArtifact.proposal_phase !== 'Phase 5.21L2V3AD') errors.push('L2V3AD review plan artifact is required');
    if (planArtifact.phase_name !== 'identity_mapping_acceptance_review_planning') {
        errors.push('L2V3AD phase_name must be identity_mapping_acceptance_review_planning');
    }
    if (planArtifact.acceptance_execution_performed !== false) {
        errors.push('L2V3AD acceptance_execution_performed must be false');
    }
    if (Number(planArtifact.accepted_mapping_count || 0) !== 0) {
        errors.push('L2V3AD accepted_mapping_count must be 0');
    }
    if (Number(planArtifact.acceptance_review_candidate_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AD acceptance_review_candidate_count must be 50');
    }
    if (Number(planArtifact.review_ready_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AD review_ready_count must be 50');
    }
    if (Number(planArtifact.review_blocked_count || 0) !== 0) {
        errors.push('L2V3AD review_blocked_count must be 0');
    }
    if (planArtifact.human_review_required !== true) errors.push('L2V3AD human_review_required must be true');
    if (hasUnsafeWriteState(planArtifact)) {
        errors.push('L2V3AD plan must not contain write-ready, DB-write, baseline, or raw retry state');
    }

    if (l2v3acArtifact.proposal_phase !== 'Phase 5.21L2V3AC') errors.push('L2V3AC artifact is required');
    if (l2v3acArtifact.verification_status !== 'passed_no_write_source_controlled') {
        errors.push('L2V3AC verification_status must be passed_no_write_source_controlled');
    }
    if (Number(l2v3acArtifact.verified_target_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AC verified_target_count must be 50');
    }
    if (Number(l2v3acArtifact.failed_target_count || 0) !== 0) errors.push('L2V3AC failed_target_count must be 0');
    if (l2v3acArtifact.raw_write_runner_blocked !== true) {
        errors.push('L2V3AC raw_write_runner_blocked must be true');
    }
    if (hasUnsafeWriteState(l2v3acArtifact)) {
        errors.push('L2V3AC must not contain write-ready, DB-write, baseline, or raw retry state');
    }
    if (Number(l2v3aaArtifact.regenerated_target_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AA regenerated_target_count must be 50');
    }
    if (hasUnsafeWriteState(l2v3aaArtifact)) {
        errors.push('L2V3AA must not contain write-ready, DB-write, baseline, or raw retry state');
    }
    if (Number(l2v3yArtifact.candidate_scope_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3Y candidate_scope_count must be 50');
    }
    if (hasUnsafeWriteState(l2v3yArtifact)) {
        errors.push('L2V3Y must not contain write-ready, DB-write, baseline, or raw retry state');
    }
    return { ok: errors.length === 0, errors };
}

function buildReviewContext(planArtifact = {}, l2v3acArtifact = {}, l2v3aaArtifact = {}, l2v3yArtifact = {}) {
    const planEntries = Array.isArray(planArtifact.review_plan_entries) ? planArtifact.review_plan_entries : [];
    const verificationResults = Array.isArray(l2v3acArtifact.verification_analysis?.target_results)
        ? l2v3acArtifact.verification_analysis.target_results
        : [];
    const enrichedTargets = Array.isArray(l2v3aaArtifact.enriched_targets) ? l2v3aaArtifact.enriched_targets : [];
    const sourceRecords = Array.isArray(l2v3yArtifact.source_inventory_metadata_records)
        ? l2v3yArtifact.source_inventory_metadata_records
        : [];
    return {
        planEntries,
        verificationByTargetId: indexBy(verificationResults, 'target_id'),
        enrichedByTargetId: indexBy(enrichedTargets, 'target_id'),
        sourceByTargetId: indexBy(sourceRecords, 'target_id'),
        duplicates: {
            target_id: countBy(planEntries.map(entry => entry.target_id)),
            match_id: countBy(planEntries.map(entry => entry.match_id)),
            source_inventory_record_key: countBy(planEntries.map(entry => entry.source_inventory_record_key)),
            source_url_fragment_external_id: countBy(planEntries.map(entry => entry.source_url_fragment_external_id)),
        },
        rawWriteRunnerBlocked: l2v3acArtifact.raw_write_runner_blocked === true,
    };
}

function buildExecutionEntry(planEntry = {}, context = {}, options = {}) {
    const blockers = [];
    const targetId = normalizeText(planEntry.target_id);
    const verification = context.verificationByTargetId.get(targetId) || {};
    const enriched = context.enrichedByTargetId.get(targetId) || {};
    const sourceRecord = context.sourceByTargetId.get(targetId) || {};
    const missingSourceEvidence =
        !normalizeText(planEntry.source_page_url) ||
        !normalizeText(planEntry.source_page_url_base) ||
        !normalizeText(planEntry.source_url_fragment_external_id) ||
        !normalizeText(planEntry.source_inventory_record_key);
    const missingScheduleMetadata =
        !normalizeText(planEntry.schedule_date) ||
        !normalizeText(planEntry.schedule_home_team) ||
        !normalizeText(planEntry.schedule_away_team);

    if (planEntry.review_status !== 'review_ready') blockers.push('plan_entry_not_review_ready');
    if (planEntry.acceptance_status !== 'not_accepted_planning_only') {
        blockers.push('plan_entry_not_planning_only');
    }
    if (verification.verification_status !== 'verified') blockers.push('verification_not_passed');
    if (missingSourceEvidence) blockers.push('missing_source_url_evidence');
    if (normalizeText(planEntry.source_url_fragment_external_id) !== normalizeText(planEntry.schedule_external_id)) {
        blockers.push('fragment_schedule_mismatch');
    }
    if (
        isDuplicate(context.duplicates.target_id, planEntry.target_id) ||
        isDuplicate(context.duplicates.match_id, planEntry.match_id)
    ) {
        blockers.push('duplicate_target_or_match_id');
    }
    if (isDuplicate(context.duplicates.source_inventory_record_key, planEntry.source_inventory_record_key)) {
        blockers.push('duplicate_source_key');
    }
    if (isDuplicate(context.duplicates.source_url_fragment_external_id, planEntry.source_url_fragment_external_id)) {
        blockers.push('duplicate_fragment_external_id');
    }
    if (missingScheduleMetadata) blockers.push('schedule_team_date_mismatch');
    if (enriched.regeneration_status !== 'regenerated_no_write') blockers.push('regeneration_status_not_clean');
    if (Array.isArray(enriched.regeneration_blockers) && enriched.regeneration_blockers.length > 0) {
        blockers.push('regeneration_blockers_present');
    }
    if (!sourceRecord.target_id) blockers.push('source_inventory_record_missing');
    if (context.rawWriteRunnerBlocked !== true) blockers.push('raw_write_runner_unexpectedly_ready');
    if (!planEntry.acceptance_evidence_summary) blockers.push('incomplete_audit_trail');
    if (options.baselineAcceptancePerformed === true) blockers.push('baseline_acceptance_already_performed');
    if (options.rawWriteRetryPerformed === true) blockers.push('raw_write_retry_already_performed');
    if (options.humanReviewSatisfied !== true) blockers.push('human_review_missing');

    const accepted = blockers.length === 0;
    return {
        target_id: planEntry.target_id || null,
        match_id: planEntry.match_id || null,
        schedule_external_id: planEntry.schedule_external_id || null,
        source_page_url: planEntry.source_page_url || null,
        source_page_url_base: planEntry.source_page_url_base || null,
        source_url_fragment_external_id: planEntry.source_url_fragment_external_id || null,
        schedule_date: planEntry.schedule_date || null,
        schedule_home_team: planEntry.schedule_home_team || null,
        schedule_away_team: planEntry.schedule_away_team || null,
        source_inventory_record_key: planEntry.source_inventory_record_key || null,
        review_status: accepted ? 'accepted' : 'review_blocked',
        review_result: accepted ? 'accepted_identity_mapping' : 'blocked_or_pending_human_acceptance',
        acceptance_status: accepted ? 'accepted_identity_mapping' : 'not_accepted',
        accepted_by: accepted ? options.acceptedBy : null,
        accepted_at: accepted ? options.acceptedAt : null,
        acceptance_blockers: blockers,
        acceptance_evidence_summary: {
            l2v3ac_verification_passed: verification.verification_status === 'verified',
            source_url_evidence_complete: missingSourceEvidence === false,
            source_url_fragment_external_id_matches_schedule_external_id:
                normalizeText(planEntry.source_url_fragment_external_id) ===
                normalizeText(planEntry.schedule_external_id),
            no_duplicate_source_inventory_record_key: !isDuplicate(
                context.duplicates.source_inventory_record_key,
                planEntry.source_inventory_record_key
            ),
            no_duplicate_source_url_fragment_external_id: !isDuplicate(
                context.duplicates.source_url_fragment_external_id,
                planEntry.source_url_fragment_external_id
            ),
            no_duplicate_target_or_match_id:
                !isDuplicate(context.duplicates.target_id, planEntry.target_id) &&
                !isDuplicate(context.duplicates.match_id, planEntry.match_id),
            schedule_team_date_metadata_present: missingScheduleMetadata === false,
            regeneration_status_regenerated_no_write: enriched.regeneration_status === 'regenerated_no_write',
            regeneration_blockers_empty:
                Array.isArray(enriched.regeneration_blockers) && enriched.regeneration_blockers.length === 0,
            raw_write_runner_remains_blocked: context.rawWriteRunnerBlocked === true,
            baseline_acceptance_performed: false,
            raw_write_retry_performed: false,
            audit_trail_complete: Boolean(planEntry.acceptance_evidence_summary && sourceRecord.target_id),
            human_review_satisfied: options.humanReviewSatisfied === true,
        },
        accepted_mapping_does_not_accept_baseline: true,
        accepted_mapping_does_not_authorize_raw_write: true,
        raw_write_eligible_after_acceptance: false,
    };
}

function executeAcceptanceReview(
    manifest = {},
    planArtifact = {},
    l2v3acArtifact = {},
    l2v3aaArtifact = {},
    l2v3yArtifact = {},
    options = {}
) {
    const context = buildReviewContext(planArtifact, l2v3acArtifact, l2v3aaArtifact, l2v3yArtifact);
    const executionOptions = {
        humanReviewSatisfied: options.humanReviewSatisfied === true,
        acceptedBy: normalizeText(options.acceptedBy) || DEFAULT_ACCEPTED_BY,
        acceptedAt: normalizeText(options.acceptedAt) || GENERATED_AT,
        baselineAcceptancePerformed: manifest.baseline_acceptance_performed === true,
        rawWriteRetryPerformed: manifest.raw_write_retry_performed === true,
    };
    const reviewEntries = context.planEntries.map(entry => buildExecutionEntry(entry, context, executionOptions));
    const acceptedMappingCount = reviewEntries.filter(
        entry => entry.acceptance_status === 'accepted_identity_mapping'
    ).length;
    const blockedMappingCount = reviewEntries.filter(
        entry => entry.acceptance_status !== 'accepted_identity_mapping'
    ).length;
    return {
        review_candidate_count: reviewEntries.length,
        reviewed_target_count: reviewEntries.length,
        accepted_mapping_count: acceptedMappingCount,
        rejected_mapping_count: 0,
        blocked_mapping_count: blockedMappingCount,
        review_blocker_count: reviewEntries.reduce((sum, entry) => sum + entry.acceptance_blockers.length, 0),
        acceptance_evidence_summary_present_count: reviewEntries.filter(entry => entry.acceptance_evidence_summary)
            .length,
        review_entries: reviewEntries,
    };
}

function determineOutcome(execution = {}, humanReviewSatisfied = false) {
    if (execution.review_candidate_count !== EXPECTED_TARGET_COUNT) return CONTINUED_PLANNING_NEXT_STEP;
    if (humanReviewSatisfied !== true || execution.blocked_mapping_count > 0) return BLOCKED_NEXT_STEP;
    if (execution.accepted_mapping_count === EXPECTED_TARGET_COUNT) return ACCEPTED_NEXT_STEP;
    return BLOCKED_NEXT_STEP;
}

function buildArtifact({
    manifest = {},
    planArtifact = {},
    execution = {},
    humanReviewSatisfied = false,
    acceptedBy = DEFAULT_ACCEPTED_BY,
    acceptedAt = GENERATED_AT,
    generatedAt = GENERATED_AT,
} = {}) {
    const outcome = determineOutcome(execution, humanReviewSatisfied);
    const identityAccepted = execution.accepted_mapping_count > 0;
    return {
        artifact_type: 'identity_mapping_acceptance_review_execution_result',
        artifact_status: identityAccepted ? ARTIFACT_STATUS : BLOCKED_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        source_phase: 'Phase 5.21L2V3AD',
        source_plan_artifact_path: L2V3AD_PLAN_PATH,
        generated_at: generatedAt,
        review_execution_only: true,
        no_write: true,
        source_controlled_artifacts_only: true,
        acceptance_review_execution_performed: true,
        live_fetch_performed: false,
        detail_fetch_performed: false,
        network_request_performed: false,
        db_write_performed: false,
        raw_insert_performed: false,
        raw_match_data_insert_performed: false,
        matches_write_performed: false,
        matches_external_id_modified: false,
        schema_migration_performed: false,
        parser_features_training_prediction_performed: false,
        browser_proxy_captcha_bypass_performed: false,
        identity_mapping_acceptance_performed: identityAccepted,
        baseline_acceptance_performed: false,
        baseline_replacement_accepted: false,
        raw_write_authorization_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        review_candidate_count: execution.review_candidate_count,
        reviewed_target_count: execution.reviewed_target_count,
        accepted_mapping_count: execution.accepted_mapping_count,
        rejected_mapping_count: execution.rejected_mapping_count,
        blocked_mapping_count: execution.blocked_mapping_count,
        review_blocker_count: execution.review_blocker_count,
        human_review_required: true,
        human_review_satisfied: humanReviewSatisfied === true,
        human_review_basis:
            humanReviewSatisfied === true
                ? 'current_user_explicitly_authorized_identity_mapping_acceptance_review_execution_in_codex_session'
                : 'missing_or_unconfirmed_human_review_evidence',
        accepted_by: identityAccepted ? acceptedBy : null,
        accepted_at: identityAccepted ? acceptedAt : null,
        acceptance_evidence_summary_present_count: execution.acceptance_evidence_summary_present_count,
        baseline_acceptance_required_next: true,
        final_db_write_authorization_required_next: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        raw_write_runner_must_remain_blocked_until_baseline_and_final_authorization: true,
        review_entries: execution.review_entries,
        upstream_context: {
            manifest_next_required_step_before_execution: manifest.next_required_step || null,
            l2v3ad_review_ready_count: planArtifact.review_ready_count || 0,
            l2v3ad_accepted_mapping_count: planArtifact.accepted_mapping_count || 0,
        },
        safety_contract: {
            review_ready_is_not_accepted_without_execution_artifact: true,
            verification_passed_is_not_accepted_mapping_without_execution_artifact: true,
            acceptance_review_execution_is_not_baseline_acceptance: true,
            acceptance_review_execution_is_not_db_write: true,
            accepted_identity_mapping_is_not_raw_write_authorization: true,
            accepted_mapping_does_not_imply_raw_write_ready_for_execution: true,
            accepted_mapping_does_not_accept_baseline: true,
            baseline_acceptance_requires_separate_authorization: true,
            final_db_write_authorization_required: true,
            raw_write_still_requires_separate_baseline_acceptance: true,
            raw_write_still_requires_separate_final_db_write_authorization: true,
        },
        recommended_next_step: outcome.recommended_next_step,
        next_required_step: outcome.next_required_step,
    };
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    const phaseStatus =
        artifact.accepted_mapping_count === EXPECTED_TARGET_COUNT
            ? 'completed_identity_mapping_acceptance_review_execution'
            : 'blocked_identity_mapping_acceptance_review_execution';
    return {
        ...manifest,
        phase_5_21_l2v3ae_execution_status: phaseStatus,
        identity_mapping_acceptance_review_execution_status: phaseStatus,
        phase_5_21_l2v3ae_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3ae_report_path: REPORT_PATH,
        acceptance_review_execution_performed: true,
        live_fetch_performed: false,
        detail_fetch_performed: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        matches_write_performed: false,
        matches_external_id_modified: false,
        phase_5_21_l2v3ae_review_candidate_count: artifact.review_candidate_count,
        phase_5_21_l2v3ae_reviewed_target_count: artifact.reviewed_target_count,
        phase_5_21_l2v3ae_accepted_mapping_count: artifact.accepted_mapping_count,
        phase_5_21_l2v3ae_rejected_mapping_count: artifact.rejected_mapping_count,
        phase_5_21_l2v3ae_blocked_mapping_count: artifact.blocked_mapping_count,
        phase_5_21_l2v3ae_human_review_required: true,
        phase_5_21_l2v3ae_human_review_satisfied: artifact.human_review_satisfied,
        phase_5_21_l2v3ae_accepted_by: artifact.accepted_by,
        phase_5_21_l2v3ae_accepted_at: artifact.accepted_at,
        identity_mapping_acceptance_review_accepted_mapping_count: artifact.accepted_mapping_count,
        identity_mapping_acceptance_review_blocked_mapping_count: artifact.blocked_mapping_count,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        accepted_mapping_does_not_imply_baseline_acceptance: true,
        accepted_mapping_does_not_imply_raw_write_authorization: true,
        accepted_mapping_does_not_imply_raw_write_ready_for_execution: true,
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

function buildReport(artifact = {}) {
    return `# Data Entrypoint Governance - Phase 5.21 L2V3AE

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- acceptance_review_execution_performed=true
- live_fetch_performed=false
- detail_fetch_performed=false
- network_request_performed=false
- db_write_performed=false
- raw_match_data_insert_performed=false
- matches_write_performed=false
- matches_external_id_modified=false
- baseline_acceptance_performed=false
- raw_write_retry_performed=false
- raw_write_ready_for_execution=false

## Execution Summary

- review_candidate_count=${artifact.review_candidate_count}
- reviewed_target_count=${artifact.reviewed_target_count}
- accepted_mapping_count=${artifact.accepted_mapping_count}
- rejected_mapping_count=${artifact.rejected_mapping_count}
- blocked_mapping_count=${artifact.blocked_mapping_count}
- review_blocker_count=${artifact.review_blocker_count}
- human_review_required=true
- human_review_satisfied=${artifact.human_review_satisfied}
- accepted_by=${artifact.accepted_by || 'null'}
- accepted_at=${artifact.accepted_at || 'null'}
- acceptance_evidence_summary_present_count=${artifact.acceptance_evidence_summary_present_count}

## Safety Contract

- review_ready is not accepted without this execution artifact.
- verification passed is not accepted mapping without this execution artifact.
- acceptance review execution is not baseline acceptance.
- acceptance review execution is not DB write.
- accepted identity mapping is not raw write authorization.
- accepted mapping does not imply raw_write_ready_for_execution.
- baseline_acceptance_performed=false.
- raw_write_retry_performed=false.
- raw_write_ready_for_execution=false.
- requires_separate_baseline_acceptance=true.
- requires_separate_final_db_write_authorization=true.

## Human Review

- human_review_basis=${artifact.human_review_basis}
- human_review_satisfied=${artifact.human_review_satisfied}

## Next Step

${artifact.recommended_next_step}
`;
}

function loadDependencies(dependencies = {}) {
    return {
        manifest: dependencies.manifest || readJsonFile(MANIFEST_PATH),
        planArtifact: dependencies.planArtifact || readJsonFile(L2V3AD_PLAN_PATH),
        l2v3acArtifact: dependencies.l2v3acArtifact || readJsonFile(L2V3AC_ARTIFACT_PATH),
        l2v3aaArtifact: dependencies.l2v3aaArtifact || readJsonFile(L2V3AA_ARTIFACT_PATH),
        l2v3yArtifact: dependencies.l2v3yArtifact || readJsonFile(L2V3Y_ARTIFACT_PATH),
    };
}

function runIdentityMappingAcceptanceReviewExecution(dependencies = {}) {
    const loaded = loadDependencies(dependencies);
    const inputGate = validateInputs(
        loaded.manifest,
        loaded.planArtifact,
        loaded.l2v3acArtifact,
        loaded.l2v3aaArtifact,
        loaded.l2v3yArtifact
    );
    if (!inputGate.ok) return { ok: false, status: 3, errors: inputGate.errors };

    const humanReviewSatisfied = dependencies.humanReviewSatisfied === true;
    const acceptedBy = normalizeText(dependencies.acceptedBy) || DEFAULT_ACCEPTED_BY;
    const acceptedAt = normalizeText(dependencies.acceptedAt) || GENERATED_AT;
    const execution = executeAcceptanceReview(
        loaded.manifest,
        loaded.planArtifact,
        loaded.l2v3acArtifact,
        loaded.l2v3aaArtifact,
        loaded.l2v3yArtifact,
        { humanReviewSatisfied, acceptedBy, acceptedAt }
    );
    const artifact = buildArtifact({
        manifest: loaded.manifest,
        planArtifact: loaded.planArtifact,
        execution,
        humanReviewSatisfied,
        acceptedBy,
        acceptedAt,
        generatedAt: dependencies.generatedAt || GENERATED_AT,
    });
    const report = buildReport(artifact);
    const updatedManifest = updateManifestMetadata(loaded.manifest, artifact);

    if (dependencies.writeFiles !== false) {
        const writeJson = dependencies.writeJsonFile || writeJsonFile;
        const writeText = dependencies.writeTextFile || writeTextFile;
        writeJson(dependencies.artifactOutputPath || ARTIFACT_OUTPUT_PATH, artifact);
        writeText(dependencies.reportOutputPath || REPORT_PATH, report);
        writeJson(dependencies.manifestOutputPath || MANIFEST_PATH, updatedManifest);
    }

    return { ok: true, status: 0, artifact, report, updated_manifest: updatedManifest };
}

function helpText() {
    return `L2V3AE is identity mapping acceptance review execution.

Allowed:
  --write-files=false
  --human-review-satisfied=yes|no
  --accepted-by=<reviewer>
  --accepted-at=<timestamp>

Blocked:
  live fetch, detail fetch, network, DB write, raw write, matches write,
  matches.external_id write, baseline acceptance, raw write retry,
  parser/features/training/prediction, browser/proxy runtime, and full payload
  printing/saving.
`;
}

function runCli(argv = process.argv.slice(2), io = {}) {
    const stdout = io.stdout || (text => process.stdout.write(text));
    const options = parseArgs(argv);
    if (options.help) {
        stdout(helpText());
        return 0;
    }
    const cliGate = validateCliOptions(options);
    if (!cliGate.ok) {
        stdout(`${JSON.stringify({ ok: false, errors: cliGate.errors }, null, 2)}\n`);
        return 2;
    }
    const result = runIdentityMappingAcceptanceReviewExecution({
        writeFiles: options.writeFiles !== false,
        humanReviewSatisfied: options.humanReviewSatisfied === true,
        acceptedBy: options.acceptedBy,
        acceptedAt: options.acceptedAt,
    });
    if (!result.ok) {
        stdout(`${JSON.stringify({ ok: false, errors: result.errors }, null, 2)}\n`);
        return result.status || 1;
    }
    stdout(
        `${JSON.stringify(
            {
                ok: true,
                phase: PHASE,
                artifact: ARTIFACT_OUTPUT_PATH,
                report: REPORT_PATH,
                accepted_mapping_count: result.artifact.accepted_mapping_count,
                blocked_mapping_count: result.artifact.blocked_mapping_count,
                human_review_satisfied: result.artifact.human_review_satisfied,
                baseline_acceptance_performed: result.artifact.baseline_acceptance_performed,
                raw_write_retry_performed: result.artifact.raw_write_retry_performed,
                raw_write_ready_for_execution: result.artifact.raw_write_ready_for_execution,
                recommended_next_step: result.artifact.recommended_next_step,
            },
            null,
            2
        )}\n`
    );
    return 0;
}

module.exports = {
    PHASE,
    PHASE_NAME,
    ARTIFACT_STATUS,
    MANIFEST_PATH,
    L2V3AD_PLAN_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_PATH,
    parseArgs,
    validateCliOptions,
    validateInputs,
    executeAcceptanceReview,
    buildArtifact,
    buildReport,
    updateManifestMetadata,
    runIdentityMappingAcceptanceReviewExecution,
    runCli,
};

if (require.main === module) {
    process.exitCode = runCli();
}
