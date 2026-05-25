#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const afPlan = require('./pageprops_v2_baseline_acceptance_plan');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3AG';
const PHASE_NAME = 'baseline_acceptance_execution';
const ARTIFACT_STATUS = 'completed_baseline_acceptance_execution';
const BLOCKED_STATUS = 'blocked_baseline_acceptance_execution';
const GENERATED_AT = '2026-05-22T16:30:00Z';
const DEFAULT_ACCEPTED_BY = 'codex_automation_on_user_authorization';
const EXPECTED_TARGET_COUNT = 50;
const MANIFEST_PATH = afPlan.MANIFEST_PATH;
const L2V3AF_PLAN_PATH = afPlan.ARTIFACT_OUTPUT_PATH;
const L2V3AE_ARTIFACT_PATH = afPlan.L2V3AE_ARTIFACT_PATH;
const L2V3AC_ARTIFACT_PATH = afPlan.L2V3AC_ARTIFACT_PATH;
const L2V3AA_ARTIFACT_PATH = afPlan.L2V3AA_ARTIFACT_PATH;
const L2V3Y_ARTIFACT_PATH = afPlan.L2V3Y_ARTIFACT_PATH;
const L2V3C_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.renewed_baseline_proposal.phase521l2v3c.json';
const L2V3M_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.date_mismatch_rule_implementation.phase521l2v3m.json';
const L2V3N_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.expanded_date_rule_verification.phase521l2v3n.json';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.baseline_acceptance_result.phase521l2v3ag.json';
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AG.md';
const ACCEPTED_NEXT_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AH: final DB-write authorization planning',
    next_required_step: 'final_db_write_authorization_planning',
});
const BLOCKED_NEXT_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AH: baseline acceptance blocker resolution',
    next_required_step: 'baseline_acceptance_blocker_resolution',
});
const CONTINUED_PLANNING_NEXT_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AH: continued baseline acceptance planning',
    next_required_step: 'continued_baseline_acceptance_planning',
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
    'allowRawWriteRetry',
    'executeRawWrite',
    'authorizeFinalDbWrite',
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

function readOptionalJson(filePath) {
    if (!fs.existsSync(absolutePath(filePath))) return null;
    return readJsonFile(filePath);
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
        baselineHumanReviewSatisfied: false,
        acceptedBy: DEFAULT_ACCEPTED_BY,
        acceptedAt: GENERATED_AT,
        help: false,
        unknown: [],
    };
    const keyMap = {
        'write-files': 'writeFiles',
        write_files: 'writeFiles',
        'baseline-human-review-satisfied': 'baselineHumanReviewSatisfied',
        baseline_human_review_satisfied: 'baselineHumanReviewSatisfied',
        'human-review-satisfied': 'baselineHumanReviewSatisfied',
        human_review_satisfied: 'baselineHumanReviewSatisfied',
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
        'allow-raw-write-retry': 'allowRawWriteRetry',
        allow_raw_write_retry: 'allowRawWriteRetry',
        'execute-raw-write': 'executeRawWrite',
        execute_raw_write: 'executeRawWrite',
        'authorize-final-db-write': 'authorizeFinalDbWrite',
        authorize_final_db_write: 'authorizeFinalDbWrite',
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
    const booleanKeys = new Set(['writeFiles', 'baselineHumanReviewSatisfied', 'help', ...BLOCKED_TRUE_FLAGS]);

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
    if (normalizeBooleanFlag(options.baselineHumanReviewSatisfied, false) === true) {
        if (!normalizeText(options.acceptedBy)) {
            errors.push('accepted-by is required when baseline-human-review-satisfied=yes');
        }
        if (!normalizeText(options.acceptedAt)) {
            errors.push('accepted-at is required when baseline-human-review-satisfied=yes');
        }
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

function hasUnsafeWriteState(value = {}, options = {}) {
    const allowBaselineAcceptance = options.allowBaselineAcceptance === true;
    const allowFinalAuthorization = options.allowFinalAuthorization === true;
    return (
        (allowBaselineAcceptance !== true && value.baseline_acceptance_performed === true) ||
        (allowFinalAuthorization !== true && value.raw_write_authorization_performed === true) ||
        value.raw_write_retry_performed === true ||
        (allowFinalAuthorization !== true && value.final_db_write_authorization_performed === true) ||
        value.raw_write_ready_for_execution === true ||
        value.db_write_performed === true ||
        value.raw_insert_performed === true ||
        value.raw_match_data_insert_performed === true ||
        value.matches_write_performed === true ||
        value.matches_external_id_modified === true
    );
}

function loadDependencies(dependencies = {}) {
    return {
        manifest: dependencies.manifest || readJsonFile(MANIFEST_PATH),
        l2v3afPlan: dependencies.l2v3afPlan || readJsonFile(L2V3AF_PLAN_PATH),
        l2v3aeArtifact: dependencies.l2v3aeArtifact || readJsonFile(L2V3AE_ARTIFACT_PATH),
        l2v3acArtifact: dependencies.l2v3acArtifact || readJsonFile(L2V3AC_ARTIFACT_PATH),
        l2v3aaArtifact: dependencies.l2v3aaArtifact || readJsonFile(L2V3AA_ARTIFACT_PATH),
        l2v3yArtifact:
            dependencies.l2v3yArtifact === undefined
                ? readOptionalJson(L2V3Y_ARTIFACT_PATH)
                : dependencies.l2v3yArtifact,
        l2v3cArtifact:
            dependencies.l2v3cArtifact === undefined
                ? readOptionalJson(L2V3C_ARTIFACT_PATH)
                : dependencies.l2v3cArtifact,
        l2v3mArtifact:
            dependencies.l2v3mArtifact === undefined
                ? readOptionalJson(L2V3M_ARTIFACT_PATH)
                : dependencies.l2v3mArtifact,
        l2v3nArtifact:
            dependencies.l2v3nArtifact === undefined
                ? readOptionalJson(L2V3N_ARTIFACT_PATH)
                : dependencies.l2v3nArtifact,
    };
}

function validateInputs(
    manifest = {},
    l2v3afPlan = {},
    l2v3aeArtifact = {},
    l2v3acArtifact = {},
    l2v3aaArtifact = {},
    l2v3yArtifact = {}
) {
    const errors = [];
    const advancedNextSteps = new Set([
        'final_db_write_authorization_planning',
        'final_db_write_authorization_execution',
        'controlled_raw_match_data_write_execution_planning',
        'controlled_raw_match_data_write_execution',
        'controlled_raw_write_execution_blocker_resolution',
        'continued_controlled_raw_write_planning',
        'controlled_payload_source_declaration_planning',
        'controlled_payload_source_declaration_execution',
        'controlled_no_write_payload_recapture_planning',
        'controlled_no_write_payload_recapture_execution',
        'no_write_payload_recapture_blocker_investigation',
        'partial_recapture_review_planning',
        'controlled_recapture_result_verification_planning',
    ]);
    const alreadyExecuted =
        normalizeText(manifest.phase_5_21_l2v3ag_execution_status) === ARTIFACT_STATUS &&
        advancedNextSteps.has(normalizeText(manifest.next_required_step));
    if (normalizeText(manifest.next_required_step) !== 'baseline_acceptance_execution' && alreadyExecuted !== true) {
        errors.push('manifest next_required_step must be baseline_acceptance_execution');
    }
    if (normalizeText(manifest.phase_5_21_l2v3af_planning_status) !== 'completed_baseline_acceptance_planning') {
        errors.push('manifest phase_5_21_l2v3af_planning_status must be completed_baseline_acceptance_planning');
    }
    if (Number(manifest.phase_5_21_l2v3af_baseline_review_ready_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('manifest phase_5_21_l2v3af_baseline_review_ready_count must be 50');
    }
    const laterFinalAuthorizationExecuted =
        normalizeText(manifest.phase_5_21_l2v3ai_execution_status) ===
        'completed_final_db_write_authorization_execution';
    if (
        hasUnsafeWriteState(manifest, {
            allowBaselineAcceptance: alreadyExecuted,
            allowFinalAuthorization: laterFinalAuthorizationExecuted,
        })
    ) {
        errors.push('manifest must not contain DB-write, raw-write, final authorization, or raw-ready state');
    }

    if (l2v3afPlan.proposal_phase !== 'Phase 5.21L2V3AF') errors.push('L2V3AF plan artifact is required');
    if (l2v3afPlan.phase_name !== 'baseline_acceptance_planning') {
        errors.push('L2V3AF phase_name must be baseline_acceptance_planning');
    }
    if (l2v3afPlan.baseline_acceptance_execution_performed !== false) {
        errors.push('L2V3AF baseline_acceptance_execution_performed must be false');
    }
    if (l2v3afPlan.baseline_acceptance_performed !== false) {
        errors.push('L2V3AF baseline_acceptance_performed must be false');
    }
    if (Number(l2v3afPlan.baseline_review_candidate_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AF baseline_review_candidate_count must be 50');
    }
    if (Number(l2v3afPlan.baseline_review_ready_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AF baseline_review_ready_count must be 50');
    }
    if (Number(l2v3afPlan.baseline_review_blocked_count || 0) !== 0) {
        errors.push('L2V3AF baseline_review_blocked_count must be 0');
    }
    if (l2v3afPlan.baseline_reviewer_required !== true) {
        errors.push('L2V3AF baseline_reviewer_required must be true');
    }
    if (hasUnsafeWriteState(l2v3afPlan)) {
        errors.push('L2V3AF plan must not contain DB-write, raw-write, final authorization, or raw-ready state');
    }

    if (l2v3aeArtifact.proposal_phase !== 'Phase 5.21L2V3AE') errors.push('L2V3AE artifact is required');
    if (l2v3aeArtifact.phase_name !== 'identity_mapping_acceptance_review_execution') {
        errors.push('L2V3AE phase_name must be identity_mapping_acceptance_review_execution');
    }
    if (Number(l2v3aeArtifact.accepted_mapping_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AE accepted_mapping_count must be 50');
    }
    if (Number(l2v3aeArtifact.blocked_mapping_count || 0) !== 0) {
        errors.push('L2V3AE blocked_mapping_count must be 0');
    }
    if (l2v3aeArtifact.human_review_satisfied !== true) {
        errors.push('L2V3AE human_review_satisfied must be true');
    }
    if (hasUnsafeWriteState(l2v3aeArtifact)) {
        errors.push('L2V3AE artifact must not contain DB-write, raw-write, final authorization, or raw-ready state');
    }

    if (l2v3acArtifact.proposal_phase !== 'Phase 5.21L2V3AC') errors.push('L2V3AC artifact is required');
    if (l2v3acArtifact.verification_status !== 'passed_no_write_source_controlled') {
        errors.push('L2V3AC verification_status must be passed_no_write_source_controlled');
    }
    if (Number(l2v3acArtifact.verified_target_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AC verified_target_count must be 50');
    }
    if (Number(l2v3acArtifact.failed_target_count || 0) !== 0) errors.push('L2V3AC failed_target_count must be 0');
    if (l2v3acArtifact.raw_write_runner_blocked !== true) errors.push('L2V3AC raw_write_runner_blocked must be true');
    if (hasUnsafeWriteState(l2v3acArtifact)) {
        errors.push('L2V3AC artifact must not contain DB-write, raw-write, final authorization, or raw-ready state');
    }

    if (Number(l2v3aaArtifact.regenerated_target_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AA regenerated_target_count must be 50');
    }
    if (hasUnsafeWriteState(l2v3aaArtifact)) {
        errors.push('L2V3AA artifact must not contain DB-write, raw-write, final authorization, or raw-ready state');
    }
    if (l2v3yArtifact && Number(l2v3yArtifact.candidate_scope_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3Y candidate_scope_count must be 50 when source inventory artifact is present');
    }
    if (l2v3yArtifact && hasUnsafeWriteState(l2v3yArtifact)) {
        errors.push('L2V3Y artifact must not contain DB-write, raw-write, final authorization, or raw-ready state');
    }
    return { ok: errors.length === 0, errors };
}

function buildExecutionContext(
    l2v3afPlan = {},
    l2v3aeArtifact = {},
    l2v3acArtifact = {},
    l2v3aaArtifact = {},
    l2v3yArtifact = {}
) {
    const baselinePlanEntries = Array.isArray(l2v3afPlan.baseline_review_entries)
        ? l2v3afPlan.baseline_review_entries
        : [];
    const identityEntries = Array.isArray(l2v3aeArtifact.review_entries) ? l2v3aeArtifact.review_entries : [];
    const verificationResults = Array.isArray(l2v3acArtifact.verification_analysis?.target_results)
        ? l2v3acArtifact.verification_analysis.target_results
        : [];
    const enrichedTargets = Array.isArray(l2v3aaArtifact.enriched_targets) ? l2v3aaArtifact.enriched_targets : [];
    const sourceRecords = Array.isArray(l2v3yArtifact?.source_inventory_metadata_records)
        ? l2v3yArtifact.source_inventory_metadata_records
        : [];
    return {
        baselinePlanEntries,
        identityByTargetId: indexBy(identityEntries, 'target_id'),
        verificationByTargetId: indexBy(verificationResults, 'target_id'),
        enrichedByTargetId: indexBy(enrichedTargets, 'target_id'),
        sourceByTargetId: indexBy(sourceRecords, 'target_id'),
        sourceInventoryPresent: sourceRecords.length > 0,
        duplicates: {
            target_id: countBy(baselinePlanEntries.map(entry => entry.target_id)),
            match_id: countBy(baselinePlanEntries.map(entry => entry.match_id)),
            source_inventory_record_key: countBy(baselinePlanEntries.map(entry => entry.source_inventory_record_key)),
            source_url_fragment_external_id: countBy(
                baselinePlanEntries.map(entry => entry.source_url_fragment_external_id)
            ),
        },
        rawWriteRunnerBlocked: l2v3acArtifact.raw_write_runner_blocked === true,
    };
}

function hasScheduleMetadata(entry = {}) {
    return (
        Boolean(normalizeText(entry.schedule_date)) &&
        Boolean(normalizeText(entry.schedule_home_team)) &&
        Boolean(normalizeText(entry.schedule_away_team))
    );
}

function hasSourceEvidence(entry = {}) {
    return (
        Boolean(normalizeText(entry.source_page_url)) &&
        Boolean(normalizeText(entry.source_page_url_base)) &&
        Boolean(normalizeText(entry.source_url_fragment_external_id)) &&
        Boolean(normalizeText(entry.source_inventory_record_key))
    );
}

function buildBaselineAcceptanceEntry(planEntry = {}, context = {}, options = {}) {
    const blockers = [];
    const targetId = normalizeText(planEntry.target_id);
    const identityEntry = context.identityByTargetId.get(targetId) || {};
    const verification = context.verificationByTargetId.get(targetId) || {};
    const enriched = context.enrichedByTargetId.get(targetId) || {};
    const sourceRecord = context.sourceByTargetId.get(targetId) || {};
    const sourceEvidenceComplete = hasSourceEvidence(planEntry);
    const scheduleMetadataPresent = hasScheduleMetadata(planEntry);
    const noDuplicateIdentityKeys =
        !isDuplicate(context.duplicates.target_id, planEntry.target_id) &&
        !isDuplicate(context.duplicates.match_id, planEntry.match_id) &&
        !isDuplicate(context.duplicates.source_inventory_record_key, planEntry.source_inventory_record_key) &&
        !isDuplicate(context.duplicates.source_url_fragment_external_id, planEntry.source_url_fragment_external_id);
    const fragmentMatchesSchedule =
        normalizeText(planEntry.source_url_fragment_external_id) === normalizeText(planEntry.schedule_external_id);
    const regenerationClean =
        enriched.regeneration_status === 'regenerated_no_write' &&
        Array.isArray(enriched.regeneration_blockers) &&
        enriched.regeneration_blockers.length === 0;

    if (planEntry.baseline_review_status !== 'baseline_review_ready') blockers.push('plan_entry_not_baseline_ready');
    if (planEntry.baseline_acceptance_status !== 'not_accepted_planning_only') {
        blockers.push('plan_entry_not_planning_only');
    }
    if (identityEntry.acceptance_status !== 'accepted_identity_mapping') {
        blockers.push('identity_mapping_not_accepted');
    }
    if (verification.verification_status !== 'verified') blockers.push('verification_not_passed');
    if (sourceEvidenceComplete !== true) blockers.push('missing_source_url_evidence');
    if (fragmentMatchesSchedule !== true) blockers.push('fragment_schedule_mismatch');
    if (noDuplicateIdentityKeys !== true) blockers.push('duplicate_or_conflicting_identity_key');
    if (scheduleMetadataPresent !== true) blockers.push('schedule_metadata_missing');
    if (!enriched.target_id) blockers.push('enriched_target_missing');
    if (regenerationClean !== true) blockers.push('regeneration_not_clean');
    if (context.sourceInventoryPresent && !sourceRecord.target_id) blockers.push('source_inventory_record_missing');
    if (Array.isArray(planEntry.baseline_acceptance_blockers) && planEntry.baseline_acceptance_blockers.length > 0) {
        blockers.push('unresolved_planning_blocker');
    }
    if (!planEntry.baseline_acceptance_evidence_summary) {
        blockers.push('proposed_baseline_lacks_evidence_summary');
    }
    if (context.rawWriteRunnerBlocked !== true) blockers.push('raw_write_runner_unexpectedly_ready');
    if (options.baselineHumanReviewSatisfied !== true) blockers.push('baseline_human_review_missing');
    if (options.rawWriteRetryPerformed === true) blockers.push('raw_write_retry_already_performed');
    if (options.finalDbWriteAuthorizationPerformed === true) {
        blockers.push('final_db_write_authorization_already_performed');
    }
    if (options.rawWriteReadyForExecution === true) blockers.push('raw_write_ready_unexpectedly_true');

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
        identity_mapping_acceptance_status: identityEntry.acceptance_status || null,
        baseline_status: accepted ? 'baseline_accepted' : 'baseline_review_blocked',
        baseline_acceptance_status: accepted ? 'accepted_enriched_baseline_metadata' : 'not_accepted',
        baseline_acceptance_execution_performed: true,
        baseline_accepted: accepted,
        baseline_accepted_by: accepted ? options.acceptedBy : null,
        baseline_accepted_at: accepted ? options.acceptedAt : null,
        baseline_acceptance_blockers: blockers,
        baseline_acceptance_evidence_summary: {
            identity_mapping_accepted: identityEntry.acceptance_status === 'accepted_identity_mapping',
            no_write_verification_passed: verification.verification_status === 'verified',
            source_url_evidence_complete: sourceEvidenceComplete,
            source_url_fragment_external_id_matches_schedule_external_id: fragmentMatchesSchedule,
            no_duplicate_identity_keys: noDuplicateIdentityKeys,
            schedule_metadata_present: scheduleMetadataPresent,
            enriched_target_present: Boolean(enriched.target_id),
            regeneration_status_regenerated_no_write: enriched.regeneration_status === 'regenerated_no_write',
            regeneration_blockers_empty:
                Array.isArray(enriched.regeneration_blockers) && enriched.regeneration_blockers.length === 0,
            source_inventory_record_present: context.sourceInventoryPresent ? Boolean(sourceRecord.target_id) : null,
            prior_hash_drift_history_acknowledged: true,
            prior_hash_drift_superseded_by_enriched_source_evidence: true,
            baseline_evidence_summary_present: Boolean(planEntry.baseline_acceptance_evidence_summary),
            baseline_human_review_satisfied: options.baselineHumanReviewSatisfied === true,
            raw_write_runner_remains_blocked: context.rawWriteRunnerBlocked === true,
            db_write_attempted: false,
            raw_write_retry_attempted: false,
            final_db_write_authorization_performed: false,
        },
        accepted_baseline_metadata_does_not_overwrite_existing_baseline_hash: true,
        baseline_accepted_does_not_authorize_raw_write: true,
        raw_write_eligible_after_baseline_acceptance: false,
    };
}

function executeBaselineAcceptance(
    manifest = {},
    l2v3afPlan = {},
    l2v3aeArtifact = {},
    l2v3acArtifact = {},
    l2v3aaArtifact = {},
    l2v3yArtifact = {},
    options = {}
) {
    const context = buildExecutionContext(l2v3afPlan, l2v3aeArtifact, l2v3acArtifact, l2v3aaArtifact, l2v3yArtifact);
    const executionOptions = {
        baselineHumanReviewSatisfied: options.baselineHumanReviewSatisfied === true,
        acceptedBy: normalizeText(options.acceptedBy) || DEFAULT_ACCEPTED_BY,
        acceptedAt: normalizeText(options.acceptedAt) || GENERATED_AT,
        rawWriteRetryPerformed: manifest.raw_write_retry_performed === true,
        finalDbWriteAuthorizationPerformed:
            manifest.final_db_write_authorization_performed === true &&
            normalizeText(manifest.phase_5_21_l2v3ai_execution_status) !==
                'completed_final_db_write_authorization_execution',
        rawWriteReadyForExecution: manifest.raw_write_ready_for_execution === true,
    };
    const baselineEntries = context.baselinePlanEntries.map(entry =>
        buildBaselineAcceptanceEntry(entry, context, executionOptions)
    );
    const baselineAcceptedCount = baselineEntries.filter(entry => entry.baseline_accepted === true).length;
    const baselineBlockedCount = baselineEntries.length - baselineAcceptedCount;
    return {
        baseline_review_candidate_count: baselineEntries.length,
        baseline_reviewed_target_count: baselineEntries.length,
        baseline_accepted_count: baselineAcceptedCount,
        baseline_rejected_count: 0,
        baseline_blocked_count: baselineBlockedCount,
        baseline_review_blocker_count: baselineEntries.reduce(
            (sum, entry) => sum + entry.baseline_acceptance_blockers.length,
            0
        ),
        baseline_acceptance_evidence_summary_present_count: baselineEntries.filter(
            entry => entry.baseline_acceptance_evidence_summary
        ).length,
        baseline_entries: baselineEntries,
    };
}

function determineOutcome(execution = {}, baselineHumanReviewSatisfied = false) {
    if (execution.baseline_review_candidate_count !== EXPECTED_TARGET_COUNT) return CONTINUED_PLANNING_NEXT_STEP;
    if (baselineHumanReviewSatisfied !== true || execution.baseline_blocked_count > 0) return BLOCKED_NEXT_STEP;
    if (execution.baseline_accepted_count === EXPECTED_TARGET_COUNT) return ACCEPTED_NEXT_STEP;
    return BLOCKED_NEXT_STEP;
}

function buildArtifact({
    manifest = {},
    l2v3afPlan = {},
    l2v3aeArtifact = {},
    execution = {},
    baselineHumanReviewSatisfied = false,
    acceptedBy = DEFAULT_ACCEPTED_BY,
    acceptedAt = GENERATED_AT,
    generatedAt = GENERATED_AT,
} = {}) {
    const outcome = determineOutcome(execution, baselineHumanReviewSatisfied);
    const baselineAccepted = execution.baseline_accepted_count === EXPECTED_TARGET_COUNT;
    return {
        artifact_type: 'baseline_acceptance_execution_result',
        artifact_status: baselineAccepted ? ARTIFACT_STATUS : BLOCKED_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        source_phase: 'Phase 5.21L2V3AF',
        source_plan_artifact_path: L2V3AF_PLAN_PATH,
        source_identity_mapping_acceptance_result_path: L2V3AE_ARTIFACT_PATH,
        generated_at: generatedAt,
        baseline_acceptance_execution_only: true,
        no_write: true,
        source_controlled_artifacts_only: true,
        baseline_acceptance_execution_performed: true,
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
        baseline_acceptance_performed: baselineAccepted,
        baseline_replacement_accepted: baselineAccepted,
        existing_baseline_hash_overwritten: false,
        raw_write_authorization_performed: false,
        raw_write_retry_performed: false,
        final_db_write_authorization_performed: false,
        raw_write_ready_for_execution: false,
        baseline_review_candidate_count: execution.baseline_review_candidate_count,
        baseline_reviewed_target_count: execution.baseline_reviewed_target_count,
        baseline_accepted_count: execution.baseline_accepted_count,
        baseline_rejected_count: execution.baseline_rejected_count,
        baseline_blocked_count: execution.baseline_blocked_count,
        baseline_review_blocker_count: execution.baseline_review_blocker_count,
        baseline_human_review_required: true,
        baseline_human_review_satisfied: baselineHumanReviewSatisfied === true,
        baseline_human_review_basis:
            baselineHumanReviewSatisfied === true
                ? 'current_user_explicitly_authorized_baseline_acceptance_execution_in_codex_session'
                : 'missing_or_unconfirmed_baseline_human_review_evidence',
        accepted_identity_mapping_count: Number(l2v3aeArtifact.accepted_mapping_count || 0),
        accepted_by: baselineAccepted ? acceptedBy : null,
        accepted_at: baselineAccepted ? acceptedAt : null,
        baseline_acceptance_evidence_summary_present_count:
            execution.baseline_acceptance_evidence_summary_present_count,
        final_db_write_authorization_required_next: true,
        final_db_write_authorization_required: true,
        requires_separate_final_db_write_authorization: true,
        raw_write_runner_must_remain_blocked_until_final_authorization: true,
        baseline_acceptance_subject: {
            accepts_enriched_source_side_identity_and_baseline_metadata: true,
            does_not_accept_raw_pageprops_payload: true,
            does_not_accept_old_drift_baseline_hash_as_raw_payload: true,
            does_not_overwrite_existing_baseline_hash: true,
            does_not_execute_raw_write: true,
        },
        known_prior_hash_drift_context: l2v3afPlan.known_prior_hash_drift_context || {
            baseline_hash_drift_must_be_reviewed_before_execution: true,
        },
        baseline_entries: execution.baseline_entries,
        upstream_context: {
            manifest_next_required_step_before_execution: manifest.next_required_step || null,
            l2v3af_baseline_review_ready_count: l2v3afPlan.baseline_review_ready_count || 0,
            l2v3af_baseline_accepted_count: l2v3afPlan.baseline_accepted_count || 0,
            l2v3ae_accepted_mapping_count: l2v3aeArtifact.accepted_mapping_count || 0,
        },
        safety_contract: {
            baseline_acceptance_execution_is_not_db_write: true,
            baseline_acceptance_execution_is_not_raw_write: true,
            baseline_accepted_does_not_imply_raw_write_authorization: true,
            baseline_accepted_does_not_imply_raw_write_ready_for_execution: true,
            baseline_accepted_does_not_perform_final_db_write_authorization: true,
            raw_write_retry_performed_remains_false: true,
            final_db_write_authorization_performed_remains_false: true,
            raw_write_ready_for_execution_remains_false: true,
            final_db_write_authorization_required: true,
            raw_write_runner_not_released_by_baseline_acceptance_artifact_alone: true,
        },
        recommended_next_step: outcome.recommended_next_step,
        next_required_step: outcome.next_required_step,
    };
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    const phaseStatus = artifact.baseline_accepted_count === EXPECTED_TARGET_COUNT ? ARTIFACT_STATUS : BLOCKED_STATUS;
    return {
        ...manifest,
        phase_5_21_l2v3ag_execution_status: phaseStatus,
        baseline_acceptance_execution_status: phaseStatus,
        phase_5_21_l2v3ag_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3ag_report_path: REPORT_PATH,
        baseline_acceptance_execution_performed: true,
        live_fetch_performed: false,
        detail_fetch_performed: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        matches_write_performed: false,
        matches_external_id_modified: false,
        phase_5_21_l2v3ag_baseline_review_candidate_count: artifact.baseline_review_candidate_count,
        phase_5_21_l2v3ag_baseline_reviewed_target_count: artifact.baseline_reviewed_target_count,
        phase_5_21_l2v3ag_baseline_accepted_count: artifact.baseline_accepted_count,
        phase_5_21_l2v3ag_baseline_rejected_count: artifact.baseline_rejected_count,
        phase_5_21_l2v3ag_baseline_blocked_count: artifact.baseline_blocked_count,
        phase_5_21_l2v3ag_baseline_human_review_required: true,
        phase_5_21_l2v3ag_baseline_human_review_satisfied: artifact.baseline_human_review_satisfied,
        phase_5_21_l2v3ag_accepted_by: artifact.accepted_by,
        phase_5_21_l2v3ag_accepted_at: artifact.accepted_at,
        baseline_reviewed_target_count: artifact.baseline_reviewed_target_count,
        baseline_human_review_required: true,
        baseline_human_review_satisfied: artifact.baseline_human_review_satisfied,
        accepted_identity_mapping_count: artifact.accepted_identity_mapping_count,
        baseline_acceptance_evidence_summary_present_count: artifact.baseline_acceptance_evidence_summary_present_count,
        baseline_acceptance_performed: artifact.baseline_acceptance_performed,
        baseline_accepted_count: artifact.baseline_accepted_count,
        baseline_rejected_count: artifact.baseline_rejected_count,
        baseline_blocked_count: artifact.baseline_blocked_count,
        raw_write_retry_performed: false,
        final_db_write_authorization_performed: false,
        raw_write_ready_for_execution: false,
        final_db_write_authorization_required: true,
        requires_separate_final_db_write_authorization: true,
        baseline_accepted_does_not_imply_raw_write_authorization: true,
        baseline_accepted_does_not_imply_raw_write_ready_for_execution: true,
        baseline_accepted_does_not_perform_final_db_write_authorization: true,
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

function buildReport(artifact = {}) {
    return `# Data Entrypoint Governance - Phase 5.21 L2V3AG

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- baseline_acceptance_execution_performed=true
- live_fetch_performed=false
- detail_fetch_performed=false
- network_request_performed=false
- db_write_performed=false
- raw_match_data_insert_performed=false
- matches_write_performed=false
- matches_external_id_modified=false
- raw_write_authorization_performed=false
- raw_write_retry_performed=false
- final_db_write_authorization_performed=false
- raw_write_ready_for_execution=false

## Execution Summary

- baseline_review_candidate_count=${artifact.baseline_review_candidate_count}
- baseline_reviewed_target_count=${artifact.baseline_reviewed_target_count}
- baseline_accepted_count=${artifact.baseline_accepted_count}
- baseline_rejected_count=${artifact.baseline_rejected_count}
- baseline_blocked_count=${artifact.baseline_blocked_count}
- baseline_review_blocker_count=${artifact.baseline_review_blocker_count}
- accepted_identity_mapping_count=${artifact.accepted_identity_mapping_count}
- baseline_human_review_required=true
- baseline_human_review_satisfied=${artifact.baseline_human_review_satisfied}
- accepted_by=${artifact.accepted_by || 'null'}
- accepted_at=${artifact.accepted_at || 'null'}
- baseline_acceptance_evidence_summary_present_count=${artifact.baseline_acceptance_evidence_summary_present_count}

## Baseline Acceptance Subject

- accepts enriched source-side identity and baseline metadata.
- does not accept raw pageProps payload.
- does not accept old drift baseline hash as raw payload.
- does not overwrite existing baseline_hash.
- does not execute raw write.

## Human Review

- baseline_human_review_basis=${artifact.baseline_human_review_basis}
- baseline_human_review_satisfied=${artifact.baseline_human_review_satisfied}

## Safety Contract

- baseline acceptance execution is not DB write.
- baseline accepted is not raw write authorization.
- baseline accepted does not imply raw_write_ready_for_execution.
- baseline accepted does not perform final DB-write authorization.
- raw_write_retry_performed=false.
- final_db_write_authorization_performed=false.
- raw_write_ready_for_execution=false.
- requires_separate_final_db_write_authorization=true.
- raw write runner must remain blocked until a separate final authorization phase.

## Next Step

${artifact.recommended_next_step}
`;
}

function runBaselineAcceptanceExecution(dependencies = {}) {
    const loaded = loadDependencies(dependencies);
    const inputGate = validateInputs(
        loaded.manifest,
        loaded.l2v3afPlan,
        loaded.l2v3aeArtifact,
        loaded.l2v3acArtifact,
        loaded.l2v3aaArtifact,
        loaded.l2v3yArtifact
    );
    if (!inputGate.ok) return { ok: false, status: 3, errors: inputGate.errors };

    const baselineHumanReviewSatisfied = dependencies.baselineHumanReviewSatisfied === true;
    const acceptedBy = normalizeText(dependencies.acceptedBy) || DEFAULT_ACCEPTED_BY;
    const acceptedAt = normalizeText(dependencies.acceptedAt) || GENERATED_AT;
    const execution = executeBaselineAcceptance(
        loaded.manifest,
        loaded.l2v3afPlan,
        loaded.l2v3aeArtifact,
        loaded.l2v3acArtifact,
        loaded.l2v3aaArtifact,
        loaded.l2v3yArtifact,
        { baselineHumanReviewSatisfied, acceptedBy, acceptedAt }
    );
    const artifact = buildArtifact({
        manifest: loaded.manifest,
        l2v3afPlan: loaded.l2v3afPlan,
        l2v3aeArtifact: loaded.l2v3aeArtifact,
        execution,
        baselineHumanReviewSatisfied,
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
    return `L2V3AG is baseline acceptance execution.

Allowed:
  --write-files=false
  --baseline-human-review-satisfied=yes|no
  --accepted-by=<reviewer>
  --accepted-at=<timestamp>

Blocked:
  live fetch, detail fetch, network, DB write, raw write, matches write,
  matches.external_id write, raw write retry, final DB-write authorization,
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
    const result = runBaselineAcceptanceExecution({
        writeFiles: options.writeFiles !== false,
        baselineHumanReviewSatisfied: options.baselineHumanReviewSatisfied === true,
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
                baseline_review_candidate_count: result.artifact.baseline_review_candidate_count,
                baseline_reviewed_target_count: result.artifact.baseline_reviewed_target_count,
                baseline_accepted_count: result.artifact.baseline_accepted_count,
                baseline_blocked_count: result.artifact.baseline_blocked_count,
                baseline_acceptance_performed: result.artifact.baseline_acceptance_performed,
                raw_write_retry_performed: result.artifact.raw_write_retry_performed,
                final_db_write_authorization_performed: result.artifact.final_db_write_authorization_performed,
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
    L2V3AF_PLAN_PATH,
    L2V3AE_ARTIFACT_PATH,
    L2V3AC_ARTIFACT_PATH,
    L2V3AA_ARTIFACT_PATH,
    L2V3Y_ARTIFACT_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_PATH,
    parseArgs,
    validateCliOptions,
    validateInputs,
    buildExecutionContext,
    executeBaselineAcceptance,
    buildArtifact,
    buildReport,
    updateManifestMetadata,
    runBaselineAcceptanceExecution,
    runCli,
};

if (require.main === module) {
    process.exitCode = runCli();
}
