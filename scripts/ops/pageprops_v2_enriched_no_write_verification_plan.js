#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3AB';
const PHASE_NAME = 'enriched_no_write_verification_planning';
const ARTIFACT_STATUS = 'completed_no_write_enriched_no_write_verification_planning';
const GENERATED_AT = '2026-05-22T03:00:00Z';
const MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const L2V3AA_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_targets.phase521l2v3aa.json';
const L2V3AA_REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AA.md';
const L2V3Y_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.controlled_source_inventory_acquisition_result.phase521l2v3y.json';
const L2V3M_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.date_mismatch_rule_implementation.phase521l2v3m.json';
const RAW_WRITE_GUARD_PATH = 'scripts/ops/renewed_pageprops_v2_raw_write_execute.js';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_no_write_verification_plan.phase521l2v3ab.json';
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AB.md';
const PLANNED_VERIFICATION_SCOPE =
    'phase521l2v3aa_current_50_enriched_targets_no_write_verification_planning_against_source_identity_evidence_and_l2v3m_date_rule_guard';
const CONTINUE_PLANNING_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AC: continued enriched no-write verification planning',
    next_required_step: 'continued_enriched_no_write_verification_planning',
});
const HELPER_IMPLEMENTATION_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AC: enriched no-write verification helper implementation',
    next_required_step: 'enriched_no_write_verification_helper_implementation',
});
const EXECUTION_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AC: controlled enriched no-write verification execution',
    next_required_step: 'controlled_enriched_no_write_verification_execution',
});
const INPUT_PATHS = Object.freeze([
    { key: 'manifest', path: MANIFEST_PATH, role: 'current_manifest', countAsArtifact: true },
    {
        key: 'l2v3aa_artifact',
        path: L2V3AA_ARTIFACT_PATH,
        role: 'enriched_targets_artifact',
        countAsArtifact: true,
    },
    {
        key: 'l2v3aa_report',
        path: L2V3AA_REPORT_PATH,
        role: 'governance_report',
        countAsArtifact: true,
    },
    {
        key: 'l2v3y_artifact',
        path: L2V3Y_ARTIFACT_PATH,
        role: 'source_inventory_acquisition_result',
        countAsArtifact: true,
    },
    {
        key: 'l2v3m_artifact',
        path: L2V3M_ARTIFACT_PATH,
        role: 'date_rule_implementation',
        countAsArtifact: true,
    },
    {
        key: 'raw_write_guard',
        path: RAW_WRITE_GUARD_PATH,
        role: 'raw_write_runner_guard',
        countAsArtifact: false,
    },
]);
const VERIFICATION_RULES = Object.freeze([
    'enriched_target_count must equal 50.',
    'each target must have source_page_url.',
    'each target must have source_page_url_base.',
    'each target must have source_url_fragment_external_id.',
    'each target must have source_inventory_record_key.',
    'source_url_fragment_external_id must equal schedule_external_id.',
    'source_inventory_record_key must be unique.',
    'source_url_fragment_external_id must be unique.',
    'target_id must be unique.',
    'match_id must be unique.',
    'schedule/team/date metadata must be present.',
    'regeneration_status must be regenerated_no_write for every target.',
    'regeneration_blockers must be empty for every target.',
    'raw_write_ready_for_execution must remain false for every target and for the manifest.',
    'enriched targets must remain consistent with the L2V3Y source inventory metadata for identity fields.',
    'L2V3M date rule blocking statuses must block verification pass, and review-only statuses must stay explicit review outcomes.',
    'raw write runner must remain blocked, and no verification planning outcome may imply accepted mapping, baseline acceptance, or final DB-write authorization.',
]);
const BLOCKED_TRUE_FLAGS = Object.freeze([
    'allowDbWrite',
    'allowNetwork',
    'allowRawMatchDataWrite',
    'allowMatchesWrite',
    'allowSchemaMigration',
    'allowParserImplementation',
    'allowFeatureExtraction',
    'allowTraining',
    'allowPrediction',
    'allowBrowserRuntime',
    'allowProxyRuntime',
    'acceptIdentityMapping',
    'acceptBaseline',
    'allowRawWriteRetry',
    'execute',
    'liveFetch',
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
        help: false,
        unknown: [],
    };
    const keyMap = {
        'write-files': 'writeFiles',
        write_files: 'writeFiles',
        'allow-db-write': 'allowDbWrite',
        allow_db_write: 'allowDbWrite',
        'allow-network': 'allowNetwork',
        allow_network: 'allowNetwork',
        'allow-raw-match-data-write': 'allowRawMatchDataWrite',
        allow_raw_match_data_write: 'allowRawMatchDataWrite',
        'allow-matches-write': 'allowMatchesWrite',
        allow_matches_write: 'allowMatchesWrite',
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
        'accept-identity-mapping': 'acceptIdentityMapping',
        accept_identity_mapping: 'acceptIdentityMapping',
        'accept-baseline': 'acceptBaseline',
        accept_baseline: 'acceptBaseline',
        'allow-raw-write-retry': 'allowRawWriteRetry',
        allow_raw_write_retry: 'allowRawWriteRetry',
        execute: 'execute',
        'live-fetch': 'liveFetch',
        live_fetch: 'liveFetch',
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

function countDuplicates(values = []) {
    const counts = new Map();
    for (const value of values) {
        const key = normalizeText(value);
        if (!key) continue;
        counts.set(key, (counts.get(key) || 0) + 1);
    }
    return [...counts.values()].filter(count => count > 1).length;
}

function countMissing(values = []) {
    return values.filter(value => !normalizeText(value)).length;
}

function countWhere(items, predicate) {
    return items.filter(predicate).length;
}

function analyzeInputPaths(paths = [], dependencies = {}) {
    return paths.map(item => {
        if (dependencies.inputPathAnalysisByPath && dependencies.inputPathAnalysisByPath[item.path]) {
            return {
                key: item.key,
                path: item.path,
                role: item.role,
                count_as_artifact: item.countAsArtifact === true,
                ...dependencies.inputPathAnalysisByPath[item.path],
            };
        }
        return {
            key: item.key,
            path: item.path,
            role: item.role,
            count_as_artifact: item.countAsArtifact === true,
            exists: fs.existsSync(absolutePath(item.path)),
        };
    });
}

function readImplementationText(filePath, dependencies = {}) {
    if (
        dependencies.sourceTextByPath &&
        Object.prototype.hasOwnProperty.call(dependencies.sourceTextByPath, filePath)
    ) {
        return dependencies.sourceTextByPath[filePath];
    }
    return readTextFile(filePath);
}

function loadDependencies(dependencies = {}) {
    return {
        manifest: dependencies.manifest || readJsonFile(MANIFEST_PATH),
        l2v3aaArtifact: dependencies.l2v3aaArtifact || readJsonFile(L2V3AA_ARTIFACT_PATH),
        l2v3aaReport: dependencies.l2v3aaReport || readTextFile(L2V3AA_REPORT_PATH),
        l2v3yArtifact: dependencies.l2v3yArtifact || readJsonFile(L2V3Y_ARTIFACT_PATH),
        l2v3mArtifact: dependencies.l2v3mArtifact || readJsonFile(L2V3M_ARTIFACT_PATH),
    };
}

function validateInputs(manifest = {}, l2v3aaArtifact = {}, l2v3aaReport = '', l2v3yArtifact = {}, l2v3mArtifact = {}) {
    const errors = [];
    const alreadyCompleted =
        normalizeText(manifest.phase_5_21_l2v3ab_planning_status) === ARTIFACT_STATUS &&
        normalizeText(manifest.enriched_no_write_verification_planning_status) === ARTIFACT_STATUS;

    if (normalizeText(manifest.next_required_step) !== 'enriched_no_write_verification_planning' && !alreadyCompleted) {
        errors.push('manifest next_required_step must be enriched_no_write_verification_planning');
    }
    if (manifest.raw_write_ready_for_execution !== false) {
        errors.push('manifest raw_write_ready_for_execution must remain false');
    }
    if (Number(manifest.accepted_mapping_count || 0) !== 0) {
        errors.push('manifest accepted_mapping_count must remain 0');
    }

    if (normalizeText(l2v3aaArtifact.proposal_phase) !== 'Phase 5.21L2V3AA') {
        errors.push('L2V3AA artifact must be present');
    }
    if (l2v3aaArtifact.regeneration_attempted !== true) {
        errors.push('L2V3AA regeneration_attempted must be true');
    }
    if (l2v3aaArtifact.live_fetch_performed !== false) {
        errors.push('L2V3AA live_fetch_performed must remain false');
    }
    if (l2v3aaArtifact.db_write_performed !== false) {
        errors.push('L2V3AA db_write_performed must remain false');
    }
    if (Number(l2v3aaArtifact.candidate_scope_count || 0) !== 50) {
        errors.push('L2V3AA candidate_scope_count must be 50');
    }
    if (Number(l2v3aaArtifact.acquired_source_record_count || 0) !== 50) {
        errors.push('L2V3AA acquired_source_record_count must be 50');
    }
    if (Number(l2v3aaArtifact.regenerated_target_count || 0) !== 50) {
        errors.push('L2V3AA regenerated_target_count must be 50');
    }
    if (Number(l2v3aaArtifact.blocked_target_count || 0) !== 0) {
        errors.push('L2V3AA blocked_target_count must remain 0');
    }
    if (Number(l2v3aaArtifact.one_to_one_mapping_count || 0) !== 50) {
        errors.push('L2V3AA one_to_one_mapping_count must be 50');
    }
    if (Number(l2v3aaArtifact.identity_evidence_complete_count || 0) !== 50) {
        errors.push('L2V3AA identity_evidence_complete_count must be 50');
    }
    if (Number(l2v3aaArtifact.raw_write_ready_target_count || 0) !== 0) {
        errors.push('L2V3AA raw_write_ready_target_count must remain 0');
    }
    if (Number(l2v3aaArtifact.accepted_mapping_count || 0) !== 0) {
        errors.push('L2V3AA accepted_mapping_count must remain 0');
    }
    if (l2v3aaArtifact.raw_write_ready_for_execution !== false) {
        errors.push('L2V3AA raw_write_ready_for_execution must remain false');
    }
    if (l2v3aaArtifact.no_write_verification_required !== true) {
        errors.push('L2V3AA no_write_verification_required must remain true');
    }
    if (!Array.isArray(l2v3aaArtifact.enriched_targets) || l2v3aaArtifact.enriched_targets.length !== 50) {
        errors.push('L2V3AA enriched_targets must contain 50 targets');
    }

    if (!normalizeText(l2v3aaReport).includes('regenerated_target_count=50')) {
        errors.push('L2V3AA report must record regenerated_target_count=50');
    }
    if (!normalizeText(l2v3aaReport).includes('no_write_verification_required=true')) {
        errors.push('L2V3AA report must record no_write_verification_required=true');
    }
    if (!normalizeText(l2v3aaReport).includes('planned_mapping_key=target_id')) {
        errors.push('L2V3AA report must record planned_mapping_key=target_id');
    }

    if (normalizeText(l2v3yArtifact.proposal_phase) !== 'Phase 5.21L2V3Y') {
        errors.push('L2V3Y artifact must be present');
    }
    if (Number(l2v3yArtifact.candidate_scope_count || 0) !== 50) {
        errors.push('L2V3Y candidate_scope_count must be 50');
    }
    if (Number(l2v3yArtifact.identity_evidence_complete_count || 0) !== 50) {
        errors.push('L2V3Y identity_evidence_complete_count must be 50');
    }
    if (Number(l2v3yArtifact.accepted_mapping_count || 0) !== 0) {
        errors.push('L2V3Y accepted_mapping_count must remain 0');
    }
    if (l2v3yArtifact.raw_write_ready_for_execution !== false) {
        errors.push('L2V3Y raw_write_ready_for_execution must remain false');
    }
    if (
        !Array.isArray(l2v3yArtifact.source_inventory_metadata_records) ||
        l2v3yArtifact.source_inventory_metadata_records.length !== 50
    ) {
        errors.push('L2V3Y source_inventory_metadata_records must contain 50 records');
    }

    if (normalizeText(l2v3mArtifact.proposal_phase) !== 'Phase 5.21L2V3M') {
        errors.push('L2V3M artifact must be present');
    }
    if (l2v3mArtifact.integrated_with_raw_write_guard !== true) {
        errors.push('L2V3M integrated_with_raw_write_guard must remain true');
    }
    if (l2v3mArtifact.raw_write_ready_for_execution !== false) {
        errors.push('L2V3M raw_write_ready_for_execution must remain false');
    }
    if (Number(l2v3mArtifact.accepted_mapping_count || 0) !== 0) {
        errors.push('L2V3M accepted_mapping_count must remain 0');
    }
    if (!Array.isArray(l2v3mArtifact.blocking_statuses) || l2v3mArtifact.blocking_statuses.length === 0) {
        errors.push('L2V3M blocking_statuses must be present');
    }

    return { ok: errors.length === 0, errors };
}

function buildHelperCoverage(l2v3aaReport = '', l2v3mArtifact = {}, dependencies = {}) {
    const guardText = readImplementationText(RAW_WRITE_GUARD_PATH, dependencies);
    return {
        raw_write_guard_validate_manifest_gate_available:
            guardText.includes('function validateManifestGate') &&
            guardText.includes('required_next_step') &&
            guardText.includes('raw_match_data_write_status'),
        l2v3m_integrated_with_raw_write_guard: l2v3mArtifact.integrated_with_raw_write_guard === true,
        l2v3aa_report_contains_regeneration_summary:
            l2v3aaReport.includes('regenerated_target_count=50') &&
            l2v3aaReport.includes('no_write_verification_required=true') &&
            l2v3aaReport.includes('planned_mapping_key=target_id'),
        checked_paths: [RAW_WRITE_GUARD_PATH, L2V3AA_REPORT_PATH, L2V3M_ARTIFACT_PATH],
    };
}

function analyzeEnrichedTargets(l2v3aaArtifact = {}, l2v3yArtifact = {}) {
    const targets = Array.isArray(l2v3aaArtifact.enriched_targets) ? l2v3aaArtifact.enriched_targets : [];
    const records = Array.isArray(l2v3yArtifact.source_inventory_metadata_records)
        ? l2v3yArtifact.source_inventory_metadata_records
        : [];
    const recordsByTargetId = new Map(records.map(record => [normalizeText(record.target_id), record]));
    const duplicateTargetIdCount = countDuplicates(targets.map(target => target.target_id));
    const duplicateMatchIdCount = countDuplicates(targets.map(target => target.match_id));
    const duplicateSourceRecordKeyCount = countDuplicates(targets.map(target => target.source_inventory_record_key));
    const duplicateFragmentExternalIdCount = countDuplicates(
        targets.map(target => target.source_url_fragment_external_id)
    );
    const missingSourcePageUrlCount = countMissing(targets.map(target => target.source_page_url));
    const missingSourcePageUrlBaseCount = countMissing(targets.map(target => target.source_page_url_base));
    const missingSourceUrlFragmentExternalIdCount = countMissing(
        targets.map(target => target.source_url_fragment_external_id)
    );
    const missingSourceInventoryRecordKeyCount = countMissing(
        targets.map(target => target.source_inventory_record_key)
    );
    const missingScheduleMetadataCount = countWhere(
        targets,
        target =>
            !normalizeText(target.schedule_external_id) ||
            !normalizeText(target.schedule_date) ||
            !normalizeText(target.schedule_home_team) ||
            !normalizeText(target.schedule_away_team)
    );
    const fragmentScheduleIdMismatchCount = countWhere(
        targets,
        target => normalizeText(target.source_url_fragment_external_id) !== normalizeText(target.schedule_external_id)
    );
    const regeneratedTargetCount = countWhere(
        targets,
        target => normalizeText(target.regeneration_status) === 'regenerated_no_write'
    );
    const nonRegeneratedTargetCount = targets.length - regeneratedTargetCount;
    const nonEmptyRegenerationBlockersCount = countWhere(
        targets,
        target => !Array.isArray(target.regeneration_blockers) || target.regeneration_blockers.length > 0
    );
    const rawWriteReadyTargetCount = countWhere(targets, target => target.raw_write_ready_for_execution !== false);
    const identityEvidenceCompleteCount = countWhere(
        targets,
        target => normalizeText(target.identity_evidence_status) === 'complete'
    );
    const enrichmentSourceArtifactMismatchCount = countWhere(
        targets,
        target => normalizeText(target.enrichment_source_artifact) !== L2V3Y_ARTIFACT_PATH
    );
    const missingSourceRecordForTargetCount = countWhere(
        targets,
        target => !recordsByTargetId.has(normalizeText(target.target_id))
    );
    const sourceInventoryConsistencyCount = countWhere(targets, target => {
        const record = recordsByTargetId.get(normalizeText(target.target_id));
        if (!record) return false;
        return (
            normalizeText(target.match_id) === normalizeText(record.match_id) &&
            normalizeText(target.schedule_external_id) === normalizeText(record.schedule_external_id) &&
            normalizeText(target.source_page_url) === normalizeText(record.source_page_url) &&
            normalizeText(target.source_page_url_base) === normalizeText(record.source_page_url_base) &&
            normalizeText(target.source_url_fragment_external_id) ===
                normalizeText(record.source_url_fragment_external_id) &&
            normalizeText(target.source_inventory_record_key) === normalizeText(record.source_inventory_record_key) &&
            normalizeText(target.source_inventory_generated_at) === normalizeText(record.source_inventory_generated_at)
        );
    });
    const summaryMismatches = [];
    if (Number(l2v3aaArtifact.regenerated_target_count || 0) !== regeneratedTargetCount) {
        summaryMismatches.push('regenerated_target_count_mismatch_from_artifact_summary');
    }
    if (Number(l2v3aaArtifact.blocked_target_count || 0) !== nonEmptyRegenerationBlockersCount) {
        summaryMismatches.push('blocked_target_count_mismatch_from_artifact_summary');
    }
    if (Number(l2v3aaArtifact.identity_evidence_complete_count || 0) !== identityEvidenceCompleteCount) {
        summaryMismatches.push('identity_evidence_complete_count_mismatch_from_artifact_summary');
    }
    if (Number(l2v3aaArtifact.raw_write_ready_target_count || 0) !== rawWriteReadyTargetCount) {
        summaryMismatches.push('raw_write_ready_target_count_mismatch_from_artifact_summary');
    }

    const blockingReasons = [];
    if (targets.length !== 50) blockingReasons.push('enriched_target_count_must_equal_50');
    if (records.length !== 50) blockingReasons.push('acquired_source_record_count_must_equal_50');
    if (duplicateTargetIdCount > 0) blockingReasons.push('duplicate_target_id_detected');
    if (duplicateMatchIdCount > 0) blockingReasons.push('duplicate_match_id_detected');
    if (duplicateSourceRecordKeyCount > 0) blockingReasons.push('duplicate_source_inventory_record_key_detected');
    if (duplicateFragmentExternalIdCount > 0) {
        blockingReasons.push('duplicate_source_url_fragment_external_id_detected');
    }
    if (missingSourcePageUrlCount > 0) blockingReasons.push('missing_source_page_url_detected');
    if (missingSourcePageUrlBaseCount > 0) blockingReasons.push('missing_source_page_url_base_detected');
    if (missingSourceUrlFragmentExternalIdCount > 0) {
        blockingReasons.push('missing_source_url_fragment_external_id_detected');
    }
    if (missingSourceInventoryRecordKeyCount > 0) blockingReasons.push('missing_source_inventory_record_key_detected');
    if (missingScheduleMetadataCount > 0) blockingReasons.push('missing_schedule_metadata_detected');
    if (fragmentScheduleIdMismatchCount > 0) blockingReasons.push('fragment_schedule_identity_mismatch_detected');
    if (nonRegeneratedTargetCount > 0) blockingReasons.push('non_regenerated_target_detected');
    if (nonEmptyRegenerationBlockersCount > 0) blockingReasons.push('regeneration_blockers_present');
    if (rawWriteReadyTargetCount > 0) blockingReasons.push('raw_write_ready_target_detected');
    if (identityEvidenceCompleteCount !== 50) blockingReasons.push('identity_evidence_complete_count_incomplete');
    if (enrichmentSourceArtifactMismatchCount > 0) blockingReasons.push('enrichment_source_artifact_mismatch_detected');
    if (missingSourceRecordForTargetCount > 0) blockingReasons.push('missing_source_record_for_target_detected');
    if (sourceInventoryConsistencyCount !== 50) blockingReasons.push('source_inventory_consistency_incomplete');
    blockingReasons.push(...summaryMismatches);

    return {
        enriched_target_count: targets.length,
        acquired_source_record_count: records.length,
        duplicate_target_id_count: duplicateTargetIdCount,
        duplicate_match_id_count: duplicateMatchIdCount,
        duplicate_source_record_key_count: duplicateSourceRecordKeyCount,
        duplicate_fragment_external_id_count: duplicateFragmentExternalIdCount,
        missing_source_page_url_count: missingSourcePageUrlCount,
        missing_source_page_url_base_count: missingSourcePageUrlBaseCount,
        missing_source_url_fragment_external_id_count: missingSourceUrlFragmentExternalIdCount,
        missing_source_inventory_record_key_count: missingSourceInventoryRecordKeyCount,
        missing_schedule_metadata_count: missingScheduleMetadataCount,
        fragment_schedule_id_mismatch_count: fragmentScheduleIdMismatchCount,
        regenerated_target_count: regeneratedTargetCount,
        non_regenerated_target_count: nonRegeneratedTargetCount,
        non_empty_regeneration_blockers_count: nonEmptyRegenerationBlockersCount,
        raw_write_ready_target_count: rawWriteReadyTargetCount,
        identity_evidence_complete_count: identityEvidenceCompleteCount,
        enrichment_source_artifact_mismatch_count: enrichmentSourceArtifactMismatchCount,
        missing_source_record_for_target_count: missingSourceRecordForTargetCount,
        source_inventory_consistency_count: sourceInventoryConsistencyCount,
        summary_mismatches: summaryMismatches,
        one_to_one_integrity_expected:
            targets.length === 50 &&
            records.length === 50 &&
            duplicateTargetIdCount === 0 &&
            duplicateMatchIdCount === 0 &&
            duplicateSourceRecordKeyCount === 0 &&
            duplicateFragmentExternalIdCount === 0 &&
            missingSourcePageUrlCount === 0 &&
            missingSourcePageUrlBaseCount === 0 &&
            missingSourceUrlFragmentExternalIdCount === 0 &&
            missingSourceInventoryRecordKeyCount === 0 &&
            missingScheduleMetadataCount === 0 &&
            fragmentScheduleIdMismatchCount === 0 &&
            nonRegeneratedTargetCount === 0 &&
            nonEmptyRegenerationBlockersCount === 0 &&
            rawWriteReadyTargetCount === 0 &&
            identityEvidenceCompleteCount === 50 &&
            enrichmentSourceArtifactMismatchCount === 0 &&
            missingSourceRecordForTargetCount === 0 &&
            sourceInventoryConsistencyCount === 50 &&
            summaryMismatches.length === 0,
        blocking_reasons: blockingReasons,
    };
}

function getRawWriteGateFunction(dependencies = {}) {
    if (typeof dependencies.rawWriteGate === 'function') return dependencies.rawWriteGate;
    if (dependencies.rawWriteModule && typeof dependencies.rawWriteModule.validateManifestGate === 'function') {
        return dependencies.rawWriteModule.validateManifestGate;
    }
    return require('./renewed_pageprops_v2_raw_write_execute').validateManifestGate;
}

function buildRawWriteGuardAnalysis(manifest = {}, dependencies = {}) {
    const validateManifestGate = getRawWriteGateFunction(dependencies);
    const gate = validateManifestGate(manifest);
    const errors = Array.isArray(gate.errors) ? gate.errors : [];
    return {
        ok: gate.ok === true,
        error_count: errors.length,
        errors_excerpt: errors.slice(0, 5),
        required_next_step: normalizeText(manifest.required_next_step) || null,
        write_execution_status: normalizeText(manifest.write_execution_status) || null,
        raw_match_data_write_status: normalizeText(manifest.raw_match_data_write_status) || null,
    };
}

function determineNextStep(verificationAnalysis = {}, helperCoverage = {}, rawWriteGuardAnalysis = {}) {
    if (helperCoverage.raw_write_guard_validate_manifest_gate_available !== true) {
        return HELPER_IMPLEMENTATION_STEP;
    }
    if (
        verificationAnalysis.one_to_one_integrity_expected !== true ||
        verificationAnalysis.blocking_reasons.length > 0 ||
        helperCoverage.l2v3m_integrated_with_raw_write_guard !== true ||
        helperCoverage.l2v3aa_report_contains_regeneration_summary !== true ||
        rawWriteGuardAnalysis.ok === true
    ) {
        return CONTINUE_PLANNING_STEP;
    }
    return EXECUTION_STEP;
}

function buildArtifact({
    manifest = {},
    l2v3aaArtifact = {},
    l2v3yArtifact = {},
    l2v3mArtifact = {},
    inputPathAnalysis = [],
    helperCoverage = {},
    verificationAnalysis = {},
    rawWriteGuardAnalysis = {},
    generatedAt = GENERATED_AT,
} = {}) {
    const nextStep = determineNextStep(verificationAnalysis, helperCoverage, rawWriteGuardAnalysis);
    return {
        artifact_type: 'enriched_no_write_verification_plan',
        artifact_status: ARTIFACT_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        source_phase: 'Phase 5.21L2V3AA',
        generated_at: generatedAt,
        no_write: true,
        live_fetch_performed: false,
        network_request_performed: false,
        db_write_performed: false,
        raw_insert_performed: false,
        raw_match_data_insert_performed: false,
        matches_write_performed: false,
        matches_external_id_modified: false,
        schema_migration_performed: false,
        parser_features_training_prediction_performed: false,
        browser_proxy_captcha_bypass_performed: false,
        verification_execution_performed: false,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        baseline_replacement_accepted: false,
        raw_write_authorization_performed: false,
        raw_write_retry_performed: false,
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
        planned_verification_scope: PLANNED_VERIFICATION_SCOPE,
        enriched_target_count: verificationAnalysis.enriched_target_count,
        planned_verification_rule_count: VERIFICATION_RULES.length,
        planned_verification_input_artifact_count: inputPathAnalysis.filter(item => item.count_as_artifact).length,
        verification_execution_authorization_required: true,
        verification_keys: [
            'target_id',
            'match_id',
            'schedule_external_id',
            'source_url_fragment_external_id',
            'source_page_url',
            'source_page_url_base',
            'source_inventory_record_key',
            'schedule_date',
            'schedule_home_team',
            'schedule_away_team',
        ],
        planned_verification_rules: VERIFICATION_RULES,
        input_analysis: inputPathAnalysis,
        helper_coverage: helperCoverage,
        verification_analysis: verificationAnalysis,
        raw_write_guard_analysis: rawWriteGuardAnalysis,
        upstream_context: {
            l2v3aa_regenerated_target_count: l2v3aaArtifact.regenerated_target_count ?? null,
            l2v3aa_blocked_target_count: l2v3aaArtifact.blocked_target_count ?? null,
            l2v3aa_no_write_verification_required: l2v3aaArtifact.no_write_verification_required ?? null,
            l2v3y_identity_evidence_complete_count: l2v3yArtifact.identity_evidence_complete_count ?? null,
            current_manifest_next_required_step: manifest.next_required_step || null,
        },
        date_rule_context: {
            integrated_with_raw_write_guard: l2v3mArtifact.integrated_with_raw_write_guard === true,
            blocking_statuses: Array.isArray(l2v3mArtifact.blocking_statuses) ? l2v3mArtifact.blocking_statuses : [],
            review_only_statuses: Array.isArray(l2v3mArtifact.review_only_statuses)
                ? l2v3mArtifact.review_only_statuses
                : [],
            positive_evidence_statuses: Array.isArray(l2v3mArtifact.positive_evidence_statuses)
                ? l2v3mArtifact.positive_evidence_statuses
                : [],
            raw_write_guard_result: {
                raw_write_ready_for_execution:
                    l2v3mArtifact.raw_write_guard_result?.raw_write_ready_for_execution ?? null,
                transaction_began: l2v3mArtifact.raw_write_guard_result?.transaction_began ?? null,
                inserted_raw_match_data_count:
                    l2v3mArtifact.raw_write_guard_result?.inserted_raw_match_data_count ?? null,
            },
        },
        safety_contract: {
            verification_plan_is_not_accepted_mapping: true,
            verification_plan_is_not_raw_write_authorization: true,
            verification_plan_is_not_identity_mapping_acceptance: true,
            verification_plan_is_not_baseline_acceptance: true,
            verification_plan_is_not_verification_execution: true,
            source_url_fragment_external_id_match_does_not_imply_accepted_mapping: true,
            identity_evidence_complete_does_not_imply_raw_write_ready_for_execution: true,
            verification_execution_requires_separate_authorization: true,
            raw_write_runner_remains_blocked: rawWriteGuardAnalysis.ok !== true,
            separate_identity_mapping_acceptance_required: true,
            separate_baseline_acceptance_required: true,
            separate_final_db_write_authorization_required: true,
        },
        recommended_next_step: nextStep.recommended_next_step,
        next_required_step: nextStep.next_required_step,
    };
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    return {
        ...manifest,
        phase_5_21_l2v3ab_planning_status: artifact.artifact_status,
        enriched_no_write_verification_planning_status: artifact.artifact_status,
        phase_5_21_l2v3ab_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3ab_report_path: REPORT_PATH,
        planned_verification_scope: artifact.planned_verification_scope,
        phase_5_21_l2v3ab_planned_verification_scope: artifact.planned_verification_scope,
        enriched_target_count: artifact.enriched_target_count,
        phase_5_21_l2v3ab_enriched_target_count: artifact.enriched_target_count,
        planned_verification_rule_count: artifact.planned_verification_rule_count,
        phase_5_21_l2v3ab_planned_verification_rule_count: artifact.planned_verification_rule_count,
        planned_verification_input_artifact_count: artifact.planned_verification_input_artifact_count,
        phase_5_21_l2v3ab_planned_verification_input_artifact_count: artifact.planned_verification_input_artifact_count,
        live_fetch_performed: false,
        db_write_performed: false,
        verification_execution_performed: false,
        accepted_mapping_count: 0,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        verification_execution_authorization_required: true,
        phase_5_21_l2v3ab_verification_execution_authorization_required: true,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

function buildReport(artifact = {}) {
    return `# Data Entrypoint Governance - Phase 5.21 L2V3AB

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- planned_verification_scope=${artifact.planned_verification_scope}
- live_fetch_performed=false
- db_write_performed=false
- verification_execution_performed=false
- identity_mapping_acceptance_performed=false
- baseline_acceptance_performed=false
- raw_write_retry_performed=false

## Classification Output

- enriched_target_count=${artifact.enriched_target_count}
- planned_verification_rule_count=${artifact.planned_verification_rule_count}
- planned_verification_input_artifact_count=${artifact.planned_verification_input_artifact_count}
- live_fetch_performed=false
- db_write_performed=false
- verification_execution_performed=false
- accepted_mapping_count=0
- raw_write_ready_for_execution=false
- verification_execution_authorization_required=true

## Verification Analysis

- duplicate_source_record_key_count=${artifact.verification_analysis.duplicate_source_record_key_count}
- duplicate_fragment_external_id_count=${artifact.verification_analysis.duplicate_fragment_external_id_count}
- missing_source_page_url_count=${artifact.verification_analysis.missing_source_page_url_count}
- missing_source_page_url_base_count=${artifact.verification_analysis.missing_source_page_url_base_count}
- missing_source_url_fragment_external_id_count=${artifact.verification_analysis.missing_source_url_fragment_external_id_count}
- missing_source_inventory_record_key_count=${artifact.verification_analysis.missing_source_inventory_record_key_count}
- fragment_schedule_id_mismatch_count=${artifact.verification_analysis.fragment_schedule_id_mismatch_count}
- non_regenerated_target_count=${artifact.verification_analysis.non_regenerated_target_count}
- non_empty_regeneration_blockers_count=${artifact.verification_analysis.non_empty_regeneration_blockers_count}
- source_inventory_consistency_count=${artifact.verification_analysis.source_inventory_consistency_count}
- one_to_one_integrity_expected=${artifact.verification_analysis.one_to_one_integrity_expected}

## Input Artifacts

${artifact.input_analysis
    .map(
        item =>
            `- ${item.role}: ${item.path} (exists=${item.exists === true}, artifact=${item.count_as_artifact === true})`
    )
    .join('\n')}

## Planned Verification Rules

${artifact.planned_verification_rules.map(rule => `- ${rule}`).join('\n')}

## Date Rule Context

- blocking_statuses=${artifact.date_rule_context.blocking_statuses.join(', ')}
- review_only_statuses=${artifact.date_rule_context.review_only_statuses.join(', ')}
- positive_evidence_statuses=${artifact.date_rule_context.positive_evidence_statuses.join(', ')}
- integrated_with_raw_write_guard=${artifact.date_rule_context.integrated_with_raw_write_guard}

## Raw Write Guard

- raw_write_guard_ok=${artifact.raw_write_guard_analysis.ok}
- raw_write_guard_error_count=${artifact.raw_write_guard_analysis.error_count}
- required_next_step=${artifact.raw_write_guard_analysis.required_next_step}
- write_execution_status=${artifact.raw_write_guard_analysis.write_execution_status}
- raw_match_data_write_status=${artifact.raw_write_guard_analysis.raw_match_data_write_status}

## Safety Contract

- verification plan is not accepted mapping.
- verification plan is not raw write authorization.
- verification plan is not identity mapping acceptance.
- verification plan is not baseline acceptance.
- verification plan is not verification execution.
- source_url_fragment_external_id match does not imply accepted mapping.
- identity_evidence_complete does not imply raw_write_ready_for_execution.
- raw write runner remains blocked.
- verification execution requires separate authorization.
- separate identity mapping acceptance is required.
- separate baseline acceptance is required.
- separate final DB-write authorization is required.

## Next Step

${artifact.recommended_next_step}
`;
}

function runEnrichedNoWriteVerificationPlan(dependencies = {}) {
    const loaded = loadDependencies(dependencies);
    const inputGate = validateInputs(
        loaded.manifest,
        loaded.l2v3aaArtifact,
        loaded.l2v3aaReport,
        loaded.l2v3yArtifact,
        loaded.l2v3mArtifact
    );
    if (!inputGate.ok) return { ok: false, status: 3, errors: inputGate.errors };

    const inputPathAnalysis = analyzeInputPaths(INPUT_PATHS, dependencies);
    const helperCoverage = buildHelperCoverage(loaded.l2v3aaReport, loaded.l2v3mArtifact, dependencies);
    const verificationAnalysis = analyzeEnrichedTargets(loaded.l2v3aaArtifact, loaded.l2v3yArtifact);
    const rawWriteGuardAnalysis = buildRawWriteGuardAnalysis(loaded.manifest, dependencies);
    let artifact = buildArtifact({
        manifest: loaded.manifest,
        l2v3aaArtifact: loaded.l2v3aaArtifact,
        l2v3yArtifact: loaded.l2v3yArtifact,
        l2v3mArtifact: loaded.l2v3mArtifact,
        inputPathAnalysis,
        helperCoverage,
        verificationAnalysis,
        rawWriteGuardAnalysis,
        generatedAt: dependencies.generatedAt || GENERATED_AT,
    });
    let updatedManifest = updateManifestMetadata(loaded.manifest, artifact);
    const updatedRawWriteGuardAnalysis = buildRawWriteGuardAnalysis(updatedManifest, dependencies);
    artifact = buildArtifact({
        manifest: loaded.manifest,
        l2v3aaArtifact: loaded.l2v3aaArtifact,
        l2v3yArtifact: loaded.l2v3yArtifact,
        l2v3mArtifact: loaded.l2v3mArtifact,
        inputPathAnalysis,
        helperCoverage,
        verificationAnalysis,
        rawWriteGuardAnalysis: updatedRawWriteGuardAnalysis,
        generatedAt: dependencies.generatedAt || GENERATED_AT,
    });
    updatedManifest = updateManifestMetadata(loaded.manifest, artifact);
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
        '  node scripts/ops/pageprops_v2_enriched_no_write_verification_plan.js --write-files=yes',
        '',
        'Safety:',
        '  L2V3AB is an enriched no-write verification planning phase.',
        '  It does not execute verification, live fetch, write DB/raw/matches, accept mappings, accept baselines, or retry raw writes.',
    ].join('\n');
}

function runCli(argv = process.argv.slice(2), streams = {}) {
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
    const result = runEnrichedNoWriteVerificationPlan({ writeFiles: options.writeFiles });
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
                planned_verification_scope: result.artifact.planned_verification_scope,
                enriched_target_count: result.artifact.enriched_target_count,
                planned_verification_rule_count: result.artifact.planned_verification_rule_count,
                planned_verification_input_artifact_count: result.artifact.planned_verification_input_artifact_count,
                live_fetch_performed: result.artifact.live_fetch_performed,
                db_write_performed: result.artifact.db_write_performed,
                verification_execution_performed: result.artifact.verification_execution_performed,
                accepted_mapping_count: result.artifact.accepted_mapping_count,
                raw_write_ready_for_execution: result.artifact.raw_write_ready_for_execution,
                verification_execution_authorization_required:
                    result.artifact.verification_execution_authorization_required,
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
    L2V3AA_ARTIFACT_PATH,
    L2V3AA_REPORT_PATH,
    L2V3Y_ARTIFACT_PATH,
    L2V3M_ARTIFACT_PATH,
    RAW_WRITE_GUARD_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_PATH,
    VERIFICATION_RULES,
    parseArgs,
    validateCliOptions,
    validateInputs,
    analyzeEnrichedTargets,
    buildRawWriteGuardAnalysis,
    buildArtifact,
    updateManifestMetadata,
    buildReport,
    runEnrichedNoWriteVerificationPlan,
    runCli,
};

if (require.main === module) {
    try {
        process.exitCode = runCli();
    } catch (error) {
        process.stdout.write(`${JSON.stringify({ ok: false, phase: PHASE, error: error.message }, null, 2)}\n`);
        process.exitCode = 1;
    }
}
