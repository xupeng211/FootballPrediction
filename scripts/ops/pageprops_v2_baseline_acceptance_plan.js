#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3AF';
const PHASE_NAME = 'baseline_acceptance_planning';
const ARTIFACT_STATUS = 'completed_baseline_acceptance_planning';
const BLOCKED_STATUS = 'blocked_baseline_acceptance_planning';
const GENERATED_AT = '2026-05-22T11:40:00Z';
const EXPECTED_TARGET_COUNT = 50;
const MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const L2V3AE_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.identity_mapping_acceptance_result.phase521l2v3ae.json';
const L2V3AC_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_no_write_verification_result.phase521l2v3ac.json';
const L2V3AA_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_targets.phase521l2v3aa.json';
const L2V3Y_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.controlled_source_inventory_acquisition_result.phase521l2v3y.json';
const L2V3C_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.renewed_baseline_proposal.phase521l2v3c.json';
const L2V3M_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.date_mismatch_rule_implementation.phase521l2v3m.json';
const L2V3N_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.expanded_date_rule_verification.phase521l2v3n.json';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.baseline_acceptance_plan.phase521l2v3af.json';
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AF.md';
const PASS_NEXT_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AG: baseline acceptance execution',
    next_required_step: 'baseline_acceptance_execution',
});
const BLOCKER_NEXT_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AG: baseline acceptance blocker investigation',
    next_required_step: 'baseline_acceptance_blocker_investigation',
});
const CONTINUED_PLANNING_NEXT_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AG: continued baseline acceptance planning',
    next_required_step: 'continued_baseline_acceptance_planning',
});
const INPUT_PATHS = Object.freeze([
    { key: 'manifest', path: MANIFEST_PATH, role: 'current_proposal_manifest', countAsArtifact: true },
    { key: 'l2v3aeArtifact', path: L2V3AE_ARTIFACT_PATH, role: 'identity_mapping_acceptance_result' },
    { key: 'l2v3acArtifact', path: L2V3AC_ARTIFACT_PATH, role: 'no_write_verification_result' },
    { key: 'l2v3aaArtifact', path: L2V3AA_ARTIFACT_PATH, role: 'enriched_targets' },
    { key: 'l2v3yArtifact', path: L2V3Y_ARTIFACT_PATH, role: 'source_inventory_acquisition_result' },
    { key: 'l2v3cArtifact', path: L2V3C_ARTIFACT_PATH, role: 'prior_renewed_baseline_proposal' },
    { key: 'l2v3mArtifact', path: L2V3M_ARTIFACT_PATH, role: 'date_route_rule_history' },
    { key: 'l2v3nArtifact', path: L2V3N_ARTIFACT_PATH, role: 'expanded_date_rule_history' },
]);
const BASELINE_REVIEW_STATUSES = Object.freeze([
    'baseline_review_not_started',
    'baseline_review_ready',
    'baseline_review_blocked',
    'baseline_accepted',
    'baseline_rejected',
    'baseline_superseded',
]);
const PLANNED_BASELINE_ACCEPTANCE_RULES = Object.freeze([
    'candidate must have accepted identity mapping in L2V3AE.',
    'candidate must have passed L2V3AC no-write verification.',
    'source URL evidence must be complete.',
    'source_url_fragment_external_id must equal schedule_external_id.',
    'target_id, match_id, source_inventory_record_key, and source_url_fragment_external_id must be unique.',
    'schedule date, home team, and away team metadata must be present.',
    'enriched target regeneration must be regenerated_no_write with no blockers.',
    'source inventory acquisition evidence must be available for the target.',
    'prior hash drift, date rule, and route rule history must be reviewed in future execution.',
    'baseline acceptance accepts enriched source-side identity and baseline metadata only.',
    'raw write runner must remain blocked and raw_write_ready_for_execution must remain false.',
    'baseline reviewer is required; accepted_by and accepted_at are only set in future execution.',
]);
const PLANNED_BASELINE_BLOCKING_RULES = Object.freeze([
    'accepted_mapping_count_not_50',
    'verification_not_passed',
    'missing_source_url_evidence',
    'duplicate_or_conflicting_identity_key',
    'schedule_metadata_missing',
    'regeneration_not_clean',
    'source_inventory_record_missing',
    'unresolved_date_or_route_blocker',
    'baseline_hash_drift_unresolved',
    'proposed_baseline_lacks_evidence_summary',
    'human_review_missing',
    'raw_write_runner_unexpectedly_ready_or_any_write_attempted',
]);
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
    'executeBaselineAcceptance',
    'acceptBaseline',
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
    const options = { writeFiles: true, help: false, unknown: [] };
    const keyMap = {
        'write-files': 'writeFiles',
        write_files: 'writeFiles',
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
        'execute-baseline-acceptance': 'executeBaselineAcceptance',
        execute_baseline_acceptance: 'executeBaselineAcceptance',
        'accept-baseline': 'acceptBaseline',
        accept_baseline: 'acceptBaseline',
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
    const booleanKeys = new Set(['writeFiles', 'help', ...BLOCKED_TRUE_FLAGS]);

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
        value.baseline_acceptance_execution_performed === true ||
        value.baseline_acceptance_performed === true ||
        value.baseline_replacement_accepted === true ||
        value.raw_write_authorization_performed === true ||
        value.raw_write_retry_performed === true ||
        value.raw_write_ready_for_execution === true ||
        value.db_write_performed === true ||
        value.raw_match_data_insert_performed === true ||
        value.matches_write_performed === true ||
        value.matches_external_id_modified === true
    );
}

function readOptionalJson(filePath) {
    if (!fs.existsSync(absolutePath(filePath))) return null;
    return readJsonFile(filePath);
}

function loadDependencies(dependencies = {}) {
    return {
        manifest: dependencies.manifest || readJsonFile(MANIFEST_PATH),
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
    l2v3aeArtifact = {},
    l2v3acArtifact = {},
    l2v3aaArtifact = {},
    l2v3yArtifact = {}
) {
    const errors = [];
    const alreadyPlanned =
        normalizeText(manifest.phase_5_21_l2v3af_planning_status) === ARTIFACT_STATUS &&
        normalizeText(manifest.next_required_step) === 'baseline_acceptance_execution';
    if (normalizeText(manifest.next_required_step) !== 'baseline_acceptance_planning' && alreadyPlanned !== true) {
        errors.push('manifest next_required_step must be baseline_acceptance_planning');
    }
    if (hasUnsafeWriteState(manifest)) {
        errors.push('manifest must not contain baseline execution, DB-write, raw-write, or raw-ready state');
    }
    if (Number(manifest.phase_5_21_l2v3ae_accepted_mapping_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('manifest phase_5_21_l2v3ae_accepted_mapping_count must be 50');
    }

    if (l2v3aeArtifact.proposal_phase !== 'Phase 5.21L2V3AE') errors.push('L2V3AE artifact is required');
    if (l2v3aeArtifact.phase_name !== 'identity_mapping_acceptance_review_execution') {
        errors.push('L2V3AE phase_name must be identity_mapping_acceptance_review_execution');
    }
    if (l2v3aeArtifact.acceptance_review_execution_performed !== true) {
        errors.push('L2V3AE acceptance_review_execution_performed must be true');
    }
    if (Number(l2v3aeArtifact.accepted_mapping_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AE accepted_mapping_count must be 50');
    }
    if (Number(l2v3aeArtifact.blocked_mapping_count || 0) !== 0) {
        errors.push('L2V3AE blocked_mapping_count must be 0');
    }
    if (l2v3aeArtifact.human_review_required !== true || l2v3aeArtifact.human_review_satisfied !== true) {
        errors.push('L2V3AE human review must be required and satisfied');
    }
    if (!normalizeText(l2v3aeArtifact.accepted_by) || !normalizeText(l2v3aeArtifact.accepted_at)) {
        errors.push('L2V3AE accepted_by and accepted_at are required');
    }
    if (hasUnsafeWriteState(l2v3aeArtifact)) {
        errors.push('L2V3AE artifact must not contain baseline execution, DB-write, raw-write, or raw-ready state');
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
        errors.push('L2V3AC artifact must not contain baseline execution, DB-write, raw-write, or raw-ready state');
    }

    if (Number(l2v3aaArtifact.regenerated_target_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AA regenerated_target_count must be 50');
    }
    if (hasUnsafeWriteState(l2v3aaArtifact)) {
        errors.push('L2V3AA artifact must not contain baseline execution, DB-write, raw-write, or raw-ready state');
    }
    if (l2v3yArtifact && Number(l2v3yArtifact.candidate_scope_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3Y candidate_scope_count must be 50 when source inventory artifact is present');
    }
    if (l2v3yArtifact && hasUnsafeWriteState(l2v3yArtifact)) {
        errors.push('L2V3Y artifact must not contain baseline execution, DB-write, raw-write, or raw-ready state');
    }
    return { ok: errors.length === 0, errors };
}

function buildInputSummaries(loaded = {}) {
    return INPUT_PATHS.map(input => {
        const value = loaded[input.key];
        return {
            key: input.key,
            path: input.path,
            role: input.role,
            present: Boolean(value),
            proposal_phase: value?.proposal_phase || null,
            no_write: value?.no_write === true || value?.db_write_performed === false || null,
            baseline_acceptance_performed: value?.baseline_acceptance_performed === true,
            raw_write_ready_for_execution: value?.raw_write_ready_for_execution === true,
        };
    });
}

function buildReviewContext(l2v3aeArtifact = {}, l2v3acArtifact = {}, l2v3aaArtifact = {}, l2v3yArtifact = {}) {
    const acceptedEntries = Array.isArray(l2v3aeArtifact.review_entries) ? l2v3aeArtifact.review_entries : [];
    const verificationResults = Array.isArray(l2v3acArtifact.verification_analysis?.target_results)
        ? l2v3acArtifact.verification_analysis.target_results
        : [];
    const enrichedTargets = Array.isArray(l2v3aaArtifact.enriched_targets) ? l2v3aaArtifact.enriched_targets : [];
    const sourceRecords = Array.isArray(l2v3yArtifact?.source_inventory_metadata_records)
        ? l2v3yArtifact.source_inventory_metadata_records
        : [];
    return {
        acceptedEntries,
        verificationByTargetId: indexBy(verificationResults, 'target_id'),
        enrichedByTargetId: indexBy(enrichedTargets, 'target_id'),
        sourceByTargetId: indexBy(sourceRecords, 'target_id'),
        sourceInventoryPresent: sourceRecords.length > 0,
        duplicates: {
            target_id: countBy(acceptedEntries.map(entry => entry.target_id)),
            match_id: countBy(acceptedEntries.map(entry => entry.match_id)),
            source_inventory_record_key: countBy(acceptedEntries.map(entry => entry.source_inventory_record_key)),
            source_url_fragment_external_id: countBy(
                acceptedEntries.map(entry => entry.source_url_fragment_external_id)
            ),
        },
        rawWriteRunnerBlocked: l2v3acArtifact.raw_write_runner_blocked === true,
    };
}

function buildBaselinePlanEntry(acceptedEntry = {}, context = {}) {
    const blockers = [];
    const targetId = normalizeText(acceptedEntry.target_id);
    const verification = context.verificationByTargetId.get(targetId) || {};
    const enriched = context.enrichedByTargetId.get(targetId) || {};
    const sourceRecord = context.sourceByTargetId.get(targetId) || {};
    const missingSourceEvidence =
        !normalizeText(acceptedEntry.source_page_url) ||
        !normalizeText(acceptedEntry.source_page_url_base) ||
        !normalizeText(acceptedEntry.source_url_fragment_external_id) ||
        !normalizeText(acceptedEntry.source_inventory_record_key);
    const missingScheduleMetadata =
        !normalizeText(acceptedEntry.schedule_date) ||
        !normalizeText(acceptedEntry.schedule_home_team) ||
        !normalizeText(acceptedEntry.schedule_away_team);

    if (acceptedEntry.acceptance_status !== 'accepted_identity_mapping') blockers.push('identity_mapping_not_accepted');
    if (verification.verification_status !== 'verified') blockers.push('verification_not_passed');
    if (missingSourceEvidence) blockers.push('missing_source_url_evidence');
    if (
        normalizeText(acceptedEntry.source_url_fragment_external_id) !==
        normalizeText(acceptedEntry.schedule_external_id)
    ) {
        blockers.push('fragment_schedule_mismatch');
    }
    if (
        isDuplicate(context.duplicates.target_id, acceptedEntry.target_id) ||
        isDuplicate(context.duplicates.match_id, acceptedEntry.match_id)
    ) {
        blockers.push('duplicate_target_or_match_id');
    }
    if (isDuplicate(context.duplicates.source_inventory_record_key, acceptedEntry.source_inventory_record_key)) {
        blockers.push('duplicate_source_key');
    }
    if (
        isDuplicate(context.duplicates.source_url_fragment_external_id, acceptedEntry.source_url_fragment_external_id)
    ) {
        blockers.push('duplicate_fragment_external_id');
    }
    if (missingScheduleMetadata) blockers.push('schedule_metadata_missing');
    if (enriched.regeneration_status !== 'regenerated_no_write') blockers.push('regeneration_status_not_clean');
    if (Array.isArray(enriched.regeneration_blockers) && enriched.regeneration_blockers.length > 0) {
        blockers.push('regeneration_blockers_present');
    }
    if (context.sourceInventoryPresent && !sourceRecord.target_id) blockers.push('source_inventory_record_missing');
    if (context.rawWriteRunnerBlocked !== true) blockers.push('raw_write_runner_unexpectedly_ready');
    if (!acceptedEntry.acceptance_evidence_summary) blockers.push('missing_identity_acceptance_evidence_summary');

    const ready = blockers.length === 0;
    return {
        target_id: acceptedEntry.target_id || null,
        match_id: acceptedEntry.match_id || null,
        schedule_external_id: acceptedEntry.schedule_external_id || null,
        source_page_url: acceptedEntry.source_page_url || null,
        source_page_url_base: acceptedEntry.source_page_url_base || null,
        source_url_fragment_external_id: acceptedEntry.source_url_fragment_external_id || null,
        schedule_date: acceptedEntry.schedule_date || null,
        schedule_home_team: acceptedEntry.schedule_home_team || null,
        schedule_away_team: acceptedEntry.schedule_away_team || null,
        source_inventory_record_key: acceptedEntry.source_inventory_record_key || null,
        identity_mapping_acceptance_status: acceptedEntry.acceptance_status || null,
        baseline_review_status: ready ? 'baseline_review_ready' : 'baseline_review_blocked',
        baseline_acceptance_status: 'not_accepted_planning_only',
        baseline_acceptance_execution_performed: false,
        baseline_accepted: false,
        baseline_accepted_by: null,
        baseline_accepted_at: null,
        baseline_acceptance_blockers: blockers,
        baseline_acceptance_evidence_summary: {
            identity_mapping_accepted: acceptedEntry.acceptance_status === 'accepted_identity_mapping',
            no_write_verification_passed: verification.verification_status === 'verified',
            source_url_evidence_complete: missingSourceEvidence === false,
            source_url_fragment_external_id_matches_schedule_external_id:
                normalizeText(acceptedEntry.source_url_fragment_external_id) ===
                normalizeText(acceptedEntry.schedule_external_id),
            no_duplicate_identity_keys:
                !isDuplicate(context.duplicates.target_id, acceptedEntry.target_id) &&
                !isDuplicate(context.duplicates.match_id, acceptedEntry.match_id) &&
                !isDuplicate(
                    context.duplicates.source_inventory_record_key,
                    acceptedEntry.source_inventory_record_key
                ) &&
                !isDuplicate(
                    context.duplicates.source_url_fragment_external_id,
                    acceptedEntry.source_url_fragment_external_id
                ),
            schedule_metadata_present: missingScheduleMetadata === false,
            regeneration_status_regenerated_no_write: enriched.regeneration_status === 'regenerated_no_write',
            regeneration_blockers_empty:
                Array.isArray(enriched.regeneration_blockers) && enriched.regeneration_blockers.length === 0,
            source_inventory_record_present: context.sourceInventoryPresent ? Boolean(sourceRecord.target_id) : null,
            raw_write_runner_remains_blocked: context.rawWriteRunnerBlocked === true,
            accepted_mapping_is_not_baseline_acceptance: true,
            baseline_review_ready_is_not_baseline_accepted: true,
            baseline_acceptance_execution_required_separately: true,
            final_db_write_authorization_required_separately: true,
        },
        baseline_review_ready_does_not_accept_baseline: true,
        baseline_acceptance_does_not_authorize_raw_write: true,
        raw_write_eligible_after_baseline_planning: false,
    };
}

function planBaselineAcceptance(
    manifest = {},
    l2v3aeArtifact = {},
    l2v3acArtifact = {},
    l2v3aaArtifact = {},
    l2v3yArtifact = {}
) {
    const context = buildReviewContext(l2v3aeArtifact, l2v3acArtifact, l2v3aaArtifact, l2v3yArtifact);
    const baselineReviewEntries = context.acceptedEntries.map(entry => buildBaselinePlanEntry(entry, context));
    const readyCount = baselineReviewEntries.filter(
        entry => entry.baseline_review_status === 'baseline_review_ready'
    ).length;
    const blockedCount = baselineReviewEntries.length - readyCount;
    return {
        identity_mapping_accepted_count: Number(l2v3aeArtifact.accepted_mapping_count || 0),
        baseline_review_candidate_count: baselineReviewEntries.length,
        baseline_review_ready_count: readyCount,
        baseline_review_blocked_count: blockedCount,
        baseline_review_blocker_count: baselineReviewEntries.reduce(
            (sum, entry) => sum + entry.baseline_acceptance_blockers.length,
            0
        ),
        baseline_review_entries: baselineReviewEntries,
        known_prior_hash_drift_context: {
            hash_drift_review_status: manifest.hash_drift_review_status || null,
            hash_drift_classification: manifest.hash_drift_classification || null,
            hash_drift_baseline_refresh_needed: manifest.hash_drift_baseline_refresh_needed === true,
            hash_gate_status: manifest.hash_gate_status || null,
            baseline_hash_drift_must_be_reviewed_before_execution: true,
        },
    };
}

function determineOutcome(plan = {}) {
    if (plan.baseline_review_candidate_count !== EXPECTED_TARGET_COUNT) return CONTINUED_PLANNING_NEXT_STEP;
    if (plan.baseline_review_blocked_count > 0) return BLOCKER_NEXT_STEP;
    if (plan.baseline_review_ready_count === EXPECTED_TARGET_COUNT) return PASS_NEXT_STEP;
    return CONTINUED_PLANNING_NEXT_STEP;
}

function buildArtifact({ loaded = {}, plan = {}, generatedAt = GENERATED_AT } = {}) {
    const inputSummaries = buildInputSummaries(loaded);
    const outcome = determineOutcome(plan);
    return {
        artifact_type: 'baseline_acceptance_planning_result',
        artifact_status: plan.baseline_review_blocked_count === 0 ? ARTIFACT_STATUS : BLOCKED_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        source_phase: 'Phase 5.21L2V3AE',
        source_identity_mapping_acceptance_result_path: L2V3AE_ARTIFACT_PATH,
        generated_at: generatedAt,
        planning_status: plan.baseline_review_blocked_count === 0 ? ARTIFACT_STATUS : BLOCKED_STATUS,
        planning_only: true,
        baseline_acceptance_planning_only: true,
        no_write: true,
        source_controlled_artifacts_only: true,
        live_fetch_performed: false,
        detail_fetch_performed: false,
        network_request_performed: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        matches_write_performed: false,
        matches_external_id_modified: false,
        schema_migration_performed: false,
        parser_features_training_prediction_performed: false,
        browser_proxy_captcha_bypass_performed: false,
        baseline_acceptance_execution_performed: false,
        baseline_acceptance_performed: false,
        baseline_replacement_accepted: false,
        raw_write_authorization_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        reviewed_input_artifact_count: inputSummaries.filter(input => input.present).length,
        input_artifact_summaries: inputSummaries,
        identity_mapping_accepted_count: plan.identity_mapping_accepted_count,
        baseline_review_candidate_count: plan.baseline_review_candidate_count,
        baseline_review_ready_count: plan.baseline_review_ready_count,
        baseline_review_blocked_count: plan.baseline_review_blocked_count,
        baseline_review_blocker_count: plan.baseline_review_blocker_count,
        planned_baseline_acceptance_rule_count: PLANNED_BASELINE_ACCEPTANCE_RULES.length,
        planned_baseline_blocking_rule_count: PLANNED_BASELINE_BLOCKING_RULES.length,
        baseline_reviewer_required: true,
        baseline_accepted_count: 0,
        baseline_rejected_count: 0,
        baseline_superseded_count: 0,
        accepted_by: null,
        accepted_at: null,
        final_db_write_authorization_required: true,
        requires_separate_baseline_acceptance_execution: true,
        requires_separate_final_db_write_authorization: true,
        planned_baseline_acceptance_rules: PLANNED_BASELINE_ACCEPTANCE_RULES,
        planned_baseline_blocking_rules: PLANNED_BASELINE_BLOCKING_RULES,
        baseline_review_status_values: BASELINE_REVIEW_STATUSES,
        baseline_acceptance_subject: {
            accepts_enriched_source_side_identity_and_baseline_metadata: true,
            does_not_accept_raw_pageprops_payload: true,
            does_not_accept_old_drift_baseline_hash: true,
            does_not_overwrite_existing_baseline_hash: true,
            does_not_execute_raw_write: true,
        },
        known_prior_hash_drift_context: plan.known_prior_hash_drift_context,
        baseline_review_entries: plan.baseline_review_entries,
        safety_contract: {
            identity_mapping_accepted_does_not_imply_baseline_accepted: true,
            baseline_review_ready_does_not_imply_baseline_accepted: true,
            baseline_accepted_would_not_imply_raw_write_authorization: true,
            baseline_acceptance_execution_requires_separate_authorization: true,
            final_db_write_authorization_required: true,
            raw_write_ready_for_execution_remains_false: true,
            raw_write_retry_performed_remains_false: true,
        },
        recommended_next_step: outcome.recommended_next_step,
        next_required_step: outcome.next_required_step,
    };
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    return {
        ...manifest,
        phase_5_21_l2v3af_planning_status: artifact.planning_status,
        baseline_acceptance_planning_status: artifact.planning_status,
        phase_5_21_l2v3af_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3af_report_path: REPORT_PATH,
        phase_5_21_l2v3af_identity_mapping_accepted_count: artifact.identity_mapping_accepted_count,
        identity_mapping_accepted_count: artifact.identity_mapping_accepted_count,
        phase_5_21_l2v3af_baseline_review_candidate_count: artifact.baseline_review_candidate_count,
        baseline_review_candidate_count: artifact.baseline_review_candidate_count,
        phase_5_21_l2v3af_baseline_review_ready_count: artifact.baseline_review_ready_count,
        baseline_review_ready_count: artifact.baseline_review_ready_count,
        phase_5_21_l2v3af_baseline_review_blocked_count: artifact.baseline_review_blocked_count,
        baseline_review_blocked_count: artifact.baseline_review_blocked_count,
        phase_5_21_l2v3af_planned_baseline_acceptance_rule_count: artifact.planned_baseline_acceptance_rule_count,
        planned_baseline_acceptance_rule_count: artifact.planned_baseline_acceptance_rule_count,
        phase_5_21_l2v3af_planned_baseline_blocking_rule_count: artifact.planned_baseline_blocking_rule_count,
        planned_baseline_blocking_rule_count: artifact.planned_baseline_blocking_rule_count,
        baseline_reviewer_required: true,
        baseline_acceptance_execution_performed: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        requires_separate_baseline_acceptance_execution: true,
        requires_separate_final_db_write_authorization: true,
        identity_mapping_accepted_does_not_imply_baseline_acceptance: true,
        baseline_review_ready_does_not_imply_baseline_accepted: true,
        baseline_acceptance_execution_requires_separate_authorization: true,
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

function buildReport(artifact = {}) {
    return `# Data Entrypoint Governance - Phase 5.21 L2V3AF

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- baseline_acceptance_planning_only=true
- baseline_acceptance_execution_performed=false
- baseline_acceptance_performed=false
- live_fetch_performed=false
- detail_fetch_performed=false
- network_request_performed=false
- db_write_performed=false
- raw_match_data_insert_performed=false
- matches_write_performed=false
- matches_external_id_modified=false
- raw_write_retry_performed=false
- raw_write_ready_for_execution=false

## Planning Summary

- reviewed_input_artifact_count=${artifact.reviewed_input_artifact_count}
- identity_mapping_accepted_count=${artifact.identity_mapping_accepted_count}
- baseline_review_candidate_count=${artifact.baseline_review_candidate_count}
- baseline_review_ready_count=${artifact.baseline_review_ready_count}
- baseline_review_blocked_count=${artifact.baseline_review_blocked_count}
- planned_baseline_acceptance_rule_count=${artifact.planned_baseline_acceptance_rule_count}
- planned_baseline_blocking_rule_count=${artifact.planned_baseline_blocking_rule_count}
- baseline_reviewer_required=true
- final_db_write_authorization_required=true

## Baseline Acceptance Subject

- accepts enriched source-side identity and baseline metadata.
- does not accept raw pageProps payload.
- does not accept old drift baseline hash.
- does not overwrite existing baseline_hash.
- does not execute raw write.

## Safety Contract

- identity mapping accepted is not baseline acceptance.
- baseline_review_ready is not baseline accepted.
- baseline acceptance execution requires separate authorization.
- baseline accepted, if any in a future phase, is not raw write authorization.
- final DB-write authorization remains required.
- raw_write_ready_for_execution=false.

## Planned Blocking Rules

${artifact.planned_baseline_blocking_rules.map(rule => `- ${rule}`).join('\n')}

## Next Step

${artifact.recommended_next_step}
`;
}

function runBaselineAcceptancePlanning(dependencies = {}) {
    const loaded = loadDependencies(dependencies);
    const inputGate = validateInputs(
        loaded.manifest,
        loaded.l2v3aeArtifact,
        loaded.l2v3acArtifact,
        loaded.l2v3aaArtifact,
        loaded.l2v3yArtifact
    );
    if (!inputGate.ok) return { ok: false, status: 3, errors: inputGate.errors };

    const plan = planBaselineAcceptance(
        loaded.manifest,
        loaded.l2v3aeArtifact,
        loaded.l2v3acArtifact,
        loaded.l2v3aaArtifact,
        loaded.l2v3yArtifact
    );
    const artifact = buildArtifact({ loaded, plan, generatedAt: dependencies.generatedAt || GENERATED_AT });
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
    return `L2V3AF is baseline acceptance planning only.

Allowed:
  --write-files=false

Blocked:
  baseline acceptance execution, live fetch, detail fetch, network, DB write,
  raw write, matches write, matches.external_id write, raw write retry,
  final DB-write authorization, parser/features/training/prediction,
  browser/proxy runtime, and full payload printing/saving.
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
    const result = runBaselineAcceptancePlanning({ writeFiles: options.writeFiles !== false });
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
                identity_mapping_accepted_count: result.artifact.identity_mapping_accepted_count,
                baseline_review_candidate_count: result.artifact.baseline_review_candidate_count,
                baseline_review_ready_count: result.artifact.baseline_review_ready_count,
                baseline_review_blocked_count: result.artifact.baseline_review_blocked_count,
                baseline_acceptance_execution_performed: result.artifact.baseline_acceptance_execution_performed,
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
    L2V3AE_ARTIFACT_PATH,
    L2V3AC_ARTIFACT_PATH,
    L2V3AA_ARTIFACT_PATH,
    L2V3Y_ARTIFACT_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_PATH,
    PLANNED_BASELINE_ACCEPTANCE_RULES,
    PLANNED_BASELINE_BLOCKING_RULES,
    parseArgs,
    validateCliOptions,
    validateInputs,
    planBaselineAcceptance,
    buildArtifact,
    buildReport,
    updateManifestMetadata,
    runBaselineAcceptancePlanning,
    runCli,
};

if (require.main === module) {
    process.exitCode = runCli();
}
