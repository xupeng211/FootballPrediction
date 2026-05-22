#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3AC';
const PHASE_NAME = 'controlled_enriched_no_write_verification_execution';
const ARTIFACT_STATUS = 'completed_controlled_enriched_no_write_verification_execution';
const GENERATED_AT = '2026-05-22T06:00:00Z';
const MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const L2V3AB_PLAN_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_no_write_verification_plan.phase521l2v3ab.json';
const L2V3AA_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_targets.phase521l2v3aa.json';
const L2V3AA_REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AA.md';
const L2V3Y_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.controlled_source_inventory_acquisition_result.phase521l2v3y.json';
const L2V3M_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.date_mismatch_rule_implementation.phase521l2v3m.json';
const RAW_WRITE_GUARD_PATH = 'scripts/ops/renewed_pageprops_v2_raw_write_execute.js';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_no_write_verification_result.phase521l2v3ac.json';
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AC.md';
const EXPECTED_TARGET_COUNT = 50;
const SOURCE_INVENTORY_ARTIFACT_PATH = L2V3Y_ARTIFACT_PATH;
const PASS_NEXT_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AD: identity mapping acceptance review planning',
    next_required_step: 'identity_mapping_acceptance_review_planning',
});
const BLOCKER_NEXT_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AD: enriched no-write verification blocker investigation',
    next_required_step: 'enriched_no_write_verification_blocker_investigation',
});
const GUARD_REVIEW_NEXT_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AD: raw write guard review planning',
    next_required_step: 'raw_write_guard_review_planning',
});
const INPUT_PATHS = Object.freeze([
    { key: 'manifest', path: MANIFEST_PATH, role: 'current_manifest', countAsArtifact: true },
    { key: 'l2v3ab_plan', path: L2V3AB_PLAN_PATH, role: 'enriched_no_write_verification_plan', countAsArtifact: true },
    { key: 'l2v3aa_artifact', path: L2V3AA_ARTIFACT_PATH, role: 'enriched_targets_artifact', countAsArtifact: true },
    { key: 'l2v3aa_report', path: L2V3AA_REPORT_PATH, role: 'governance_report', countAsArtifact: true },
    {
        key: 'l2v3y_artifact',
        path: L2V3Y_ARTIFACT_PATH,
        role: 'source_inventory_acquisition_result',
        countAsArtifact: true,
    },
    { key: 'l2v3m_artifact', path: L2V3M_ARTIFACT_PATH, role: 'date_rule_implementation', countAsArtifact: true },
    { key: 'raw_write_guard', path: RAW_WRITE_GUARD_PATH, role: 'raw_write_runner_guard', countAsArtifact: false },
]);
const VERIFICATION_RULES = Object.freeze([
    'enriched_target_count must equal 50.',
    'each target must have source_page_url.',
    'each target must have source_page_url_base.',
    'each target must have source_url_fragment_external_id.',
    'each target must have source_inventory_record_key.',
    'source_url_fragment_external_id must equal schedule_external_id.',
    'target_id must be unique.',
    'match_id must be unique.',
    'source_inventory_record_key must be unique.',
    'source_url_fragment_external_id must be unique.',
    'schedule_date must be present.',
    'schedule_home_team must be present.',
    'schedule_away_team must be present.',
    'regeneration_status must be regenerated_no_write.',
    'regeneration_blockers must be empty.',
    'raw_write_ready_for_execution must be false for every target.',
    'raw write runner must remain blocked.',
    'accepted_mapping_count must remain 0.',
    'identity_mapping_acceptance_performed must remain false.',
    'baseline_acceptance_performed must remain false.',
    'raw_write_retry_performed must remain false.',
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
    'acceptIdentityMapping',
    'acceptBaseline',
    'acceptBaselineReplacement',
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
        'allow-live-fetch': 'allowLiveFetch',
        allow_live_fetch: 'allowLiveFetch',
        'live-fetch': 'allowLiveFetch',
        live_fetch: 'allowLiveFetch',
        'allow-detail-fetch': 'allowDetailFetch',
        allow_detail_fetch: 'allowDetailFetch',
        'detail-fetch': 'allowDetailFetch',
        detail_fetch: 'allowDetailFetch',
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
        'accept-identity-mapping': 'acceptIdentityMapping',
        accept_identity_mapping: 'acceptIdentityMapping',
        'accept-baseline': 'acceptBaseline',
        accept_baseline: 'acceptBaseline',
        'accept-baseline-replacement': 'acceptBaselineReplacement',
        accept_baseline_replacement: 'acceptBaselineReplacement',
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

function countMissing(values = []) {
    return values.filter(value => !normalizeText(value)).length;
}

function duplicateValueSet(values = []) {
    const counts = new Map();
    for (const value of values) {
        const key = normalizeText(value);
        if (!key) continue;
        counts.set(key, (counts.get(key) || 0) + 1);
    }
    return new Set([...counts.entries()].filter(([, count]) => count > 1).map(([value]) => value));
}

function countDuplicateGroups(values = []) {
    return duplicateValueSet(values).size;
}

function countWhere(items = [], predicate) {
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
        l2v3abPlan: dependencies.l2v3abPlan || readJsonFile(L2V3AB_PLAN_PATH),
        l2v3aaArtifact: dependencies.l2v3aaArtifact || readJsonFile(L2V3AA_ARTIFACT_PATH),
        l2v3aaReport: dependencies.l2v3aaReport || readTextFile(L2V3AA_REPORT_PATH),
        l2v3yArtifact: dependencies.l2v3yArtifact || readJsonFile(L2V3Y_ARTIFACT_PATH),
        l2v3mArtifact: dependencies.l2v3mArtifact || readJsonFile(L2V3M_ARTIFACT_PATH),
    };
}

function validateInputs(
    manifest = {},
    l2v3abPlan = {},
    l2v3aaArtifact = {},
    l2v3aaReport = '',
    l2v3yArtifact = {},
    l2v3mArtifact = {}
) {
    const errors = [];
    const alreadyCompleted =
        normalizeText(manifest.phase_5_21_l2v3ac_execution_status) === ARTIFACT_STATUS &&
        normalizeText(manifest.enriched_no_write_verification_execution_status) === ARTIFACT_STATUS;

    if (
        normalizeText(manifest.next_required_step) !== 'controlled_enriched_no_write_verification_execution' &&
        !alreadyCompleted
    ) {
        errors.push('manifest next_required_step must be controlled_enriched_no_write_verification_execution');
    }
    if (manifest.raw_write_ready_for_execution !== false) {
        errors.push('manifest raw_write_ready_for_execution must remain false');
    }
    if (Number(manifest.accepted_mapping_count || 0) !== 0) {
        errors.push('manifest accepted_mapping_count must remain 0');
    }
    if (manifest.identity_mapping_acceptance_performed === true) {
        errors.push('manifest identity_mapping_acceptance_performed must remain false');
    }
    if (manifest.baseline_acceptance_performed === true) {
        errors.push('manifest baseline_acceptance_performed must remain false');
    }
    if (manifest.raw_write_retry_performed === true) {
        errors.push('manifest raw_write_retry_performed must remain false');
    }

    if (normalizeText(l2v3abPlan.proposal_phase) !== 'Phase 5.21L2V3AB') errors.push('L2V3AB plan must be present');
    if (l2v3abPlan.live_fetch_performed !== false) errors.push('L2V3AB live_fetch_performed must remain false');
    if (l2v3abPlan.db_write_performed !== false) errors.push('L2V3AB db_write_performed must remain false');
    if (l2v3abPlan.verification_execution_performed !== false) {
        errors.push('L2V3AB verification_execution_performed must remain false');
    }
    if (Number(l2v3abPlan.enriched_target_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AB enriched_target_count must be 50');
    }
    if (Number(l2v3abPlan.planned_verification_rule_count || 0) !== 17) {
        errors.push('L2V3AB planned_verification_rule_count must be 17');
    }
    if (Number(l2v3abPlan.planned_verification_input_artifact_count || 0) !== 5) {
        errors.push('L2V3AB planned_verification_input_artifact_count must be 5');
    }
    if (Number(l2v3abPlan.accepted_mapping_count || 0) !== 0) {
        errors.push('L2V3AB accepted_mapping_count must remain 0');
    }
    if (l2v3abPlan.raw_write_ready_for_execution !== false) {
        errors.push('L2V3AB raw_write_ready_for_execution must remain false');
    }
    if (l2v3abPlan.verification_execution_authorization_required !== true) {
        errors.push('L2V3AB verification_execution_authorization_required must remain true');
    }

    if (normalizeText(l2v3aaArtifact.proposal_phase) !== 'Phase 5.21L2V3AA') {
        errors.push('L2V3AA artifact must be present');
    }
    if (Number(l2v3aaArtifact.regenerated_target_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3AA regenerated_target_count must be 50');
    }
    if (Number(l2v3aaArtifact.blocked_target_count || 0) !== 0) {
        errors.push('L2V3AA blocked_target_count must remain 0');
    }
    if (Number(l2v3aaArtifact.accepted_mapping_count || 0) !== 0) {
        errors.push('L2V3AA accepted_mapping_count must remain 0');
    }
    if (l2v3aaArtifact.raw_write_ready_for_execution !== false) {
        errors.push('L2V3AA raw_write_ready_for_execution must remain false');
    }
    if (
        !Array.isArray(l2v3aaArtifact.enriched_targets) ||
        l2v3aaArtifact.enriched_targets.length !== EXPECTED_TARGET_COUNT
    ) {
        errors.push('L2V3AA enriched_targets must contain 50 targets');
    }

    if (!normalizeText(l2v3aaReport).includes('regenerated_target_count=50')) {
        errors.push('L2V3AA report must record regenerated_target_count=50');
    }
    if (!normalizeText(l2v3aaReport).includes('no_write_verification_required=true')) {
        errors.push('L2V3AA report must record no_write_verification_required=true');
    }

    if (normalizeText(l2v3yArtifact.proposal_phase) !== 'Phase 5.21L2V3Y') {
        errors.push('L2V3Y artifact must be present');
    }
    if (Number(l2v3yArtifact.candidate_scope_count || 0) !== EXPECTED_TARGET_COUNT) {
        errors.push('L2V3Y candidate_scope_count must be 50');
    }
    if (Number(l2v3yArtifact.accepted_mapping_count || 0) !== 0) {
        errors.push('L2V3Y accepted_mapping_count must remain 0');
    }
    if (l2v3yArtifact.raw_write_ready_for_execution !== false) {
        errors.push('L2V3Y raw_write_ready_for_execution must remain false');
    }
    if (
        !Array.isArray(l2v3yArtifact.source_inventory_metadata_records) ||
        l2v3yArtifact.source_inventory_metadata_records.length !== EXPECTED_TARGET_COUNT
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

    return { ok: errors.length === 0, errors };
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
        blocked: gate.ok !== true,
        error_count: errors.length,
        errors_excerpt: errors.slice(0, 5),
        required_next_step: normalizeText(manifest.required_next_step) || null,
        next_required_step: normalizeText(manifest.next_required_step) || null,
        write_execution_status: normalizeText(manifest.write_execution_status) || null,
        raw_match_data_write_status: normalizeText(manifest.raw_match_data_write_status) || null,
    };
}

function buildHelperCoverage(l2v3abPlan = {}, l2v3mArtifact = {}, dependencies = {}) {
    const guardText = readImplementationText(RAW_WRITE_GUARD_PATH, dependencies);
    return {
        l2v3ab_plan_authorizes_verification_execution:
            normalizeText(l2v3abPlan.next_required_step) === 'controlled_enriched_no_write_verification_execution' &&
            l2v3abPlan.verification_execution_authorization_required === true,
        raw_write_guard_validate_manifest_gate_available:
            guardText.includes('function validateManifestGate') &&
            guardText.includes('required_next_step') &&
            guardText.includes('raw_match_data_write_status'),
        l2v3m_integrated_with_raw_write_guard: l2v3mArtifact.integrated_with_raw_write_guard === true,
        checked_paths: [L2V3AB_PLAN_PATH, RAW_WRITE_GUARD_PATH, L2V3M_ARTIFACT_PATH],
    };
}

function sourceInventoryRecordMap(l2v3yArtifact = {}) {
    const records = Array.isArray(l2v3yArtifact.source_inventory_metadata_records)
        ? l2v3yArtifact.source_inventory_metadata_records
        : [];
    return new Map(records.map(record => [normalizeText(record.target_id), record]));
}

function buildTargetRuleFailures(target = {}, duplicates = {}, recordsByTargetId = new Map()) {
    const failures = [];
    const sourceRecord = recordsByTargetId.get(normalizeText(target.target_id));
    if (!normalizeText(target.source_page_url)) failures.push('missing_source_page_url');
    if (!normalizeText(target.source_page_url_base)) failures.push('missing_source_page_url_base');
    if (!normalizeText(target.source_url_fragment_external_id)) {
        failures.push('missing_source_url_fragment_external_id');
    }
    if (!normalizeText(target.source_inventory_record_key)) failures.push('missing_source_inventory_record_key');
    if (normalizeText(target.source_url_fragment_external_id) !== normalizeText(target.schedule_external_id)) {
        failures.push('source_url_fragment_external_id_mismatch');
    }
    if (duplicates.targetIds.has(normalizeText(target.target_id))) failures.push('duplicate_target_id');
    if (duplicates.matchIds.has(normalizeText(target.match_id))) failures.push('duplicate_match_id');
    if (duplicates.sourceRecordKeys.has(normalizeText(target.source_inventory_record_key))) {
        failures.push('duplicate_source_inventory_record_key');
    }
    if (duplicates.fragmentExternalIds.has(normalizeText(target.source_url_fragment_external_id))) {
        failures.push('duplicate_source_url_fragment_external_id');
    }
    if (!normalizeText(target.schedule_date)) failures.push('missing_schedule_date');
    if (!normalizeText(target.schedule_home_team)) failures.push('missing_schedule_home_team');
    if (!normalizeText(target.schedule_away_team)) failures.push('missing_schedule_away_team');
    if (normalizeText(target.regeneration_status) !== 'regenerated_no_write') {
        failures.push('invalid_regeneration_status');
    }
    if (!Array.isArray(target.regeneration_blockers) || target.regeneration_blockers.length > 0) {
        failures.push('regeneration_blockers_present');
    }
    if (target.raw_write_ready_for_execution !== false) failures.push('raw_write_ready_target');
    if (!sourceRecord) {
        failures.push('missing_source_inventory_record');
    } else if (
        normalizeText(sourceRecord.match_id) !== normalizeText(target.match_id) ||
        normalizeText(sourceRecord.schedule_external_id) !== normalizeText(target.schedule_external_id) ||
        normalizeText(sourceRecord.source_page_url) !== normalizeText(target.source_page_url) ||
        normalizeText(sourceRecord.source_page_url_base) !== normalizeText(target.source_page_url_base) ||
        normalizeText(sourceRecord.source_url_fragment_external_id) !==
            normalizeText(target.source_url_fragment_external_id) ||
        normalizeText(sourceRecord.source_inventory_record_key) !== normalizeText(target.source_inventory_record_key)
    ) {
        failures.push('source_inventory_record_mismatch');
    }
    if (normalizeText(target.enrichment_source_artifact) !== SOURCE_INVENTORY_ARTIFACT_PATH) {
        failures.push('enrichment_source_artifact_mismatch');
    }
    return failures;
}

function analyzeEnrichedTargets(l2v3aaArtifact = {}, l2v3yArtifact = {}) {
    const targets = Array.isArray(l2v3aaArtifact.enriched_targets) ? l2v3aaArtifact.enriched_targets : [];
    const recordsByTargetId = sourceInventoryRecordMap(l2v3yArtifact);
    const duplicates = {
        targetIds: duplicateValueSet(targets.map(target => target.target_id)),
        matchIds: duplicateValueSet(targets.map(target => target.match_id)),
        sourceRecordKeys: duplicateValueSet(targets.map(target => target.source_inventory_record_key)),
        fragmentExternalIds: duplicateValueSet(targets.map(target => target.source_url_fragment_external_id)),
    };
    const targetResults = targets.map(target => {
        const failures = buildTargetRuleFailures(target, duplicates, recordsByTargetId);
        return {
            target_id: normalizeText(target.target_id),
            match_id: normalizeText(target.match_id),
            schedule_external_id: normalizeText(target.schedule_external_id),
            source_url_fragment_external_id: normalizeText(target.source_url_fragment_external_id),
            verification_status: failures.length === 0 ? 'verified' : 'blocked',
            failure_reasons: failures,
        };
    });
    const blockedTargetCount = countWhere(targetResults, result => result.verification_status !== 'verified');
    const sourceUrlEvidenceCompleteCount = countWhere(
        targets,
        target =>
            normalizeText(target.source_page_url) &&
            normalizeText(target.source_page_url_base) &&
            normalizeText(target.source_url_fragment_external_id) &&
            normalizeText(target.source_inventory_record_key)
    );
    const fragmentScheduleIdMatchCount = countWhere(
        targets,
        target =>
            normalizeText(target.source_url_fragment_external_id) &&
            normalizeText(target.source_url_fragment_external_id) === normalizeText(target.schedule_external_id)
    );
    const missingScheduleDateCount = countMissing(targets.map(target => target.schedule_date));
    const missingScheduleHomeTeamCount = countMissing(targets.map(target => target.schedule_home_team));
    const missingScheduleAwayTeamCount = countMissing(targets.map(target => target.schedule_away_team));
    const missingRequiredMetadataCount = countWhere(
        targets,
        target =>
            !normalizeText(target.schedule_date) ||
            !normalizeText(target.schedule_home_team) ||
            !normalizeText(target.schedule_away_team) ||
            !normalizeText(target.source_page_url) ||
            !normalizeText(target.source_page_url_base) ||
            !normalizeText(target.source_url_fragment_external_id) ||
            !normalizeText(target.source_inventory_record_key)
    );
    const regenerationStatusValidCount = countWhere(
        targets,
        target => normalizeText(target.regeneration_status) === 'regenerated_no_write'
    );
    const regenerationBlockersCount = countWhere(
        targets,
        target => !Array.isArray(target.regeneration_blockers) || target.regeneration_blockers.length > 0
    );
    const rawWriteReadyTargetCount = countWhere(targets, target => target.raw_write_ready_for_execution !== false);
    const sourceInventoryConsistencyCount = countWhere(
        targetResults,
        result =>
            !result.failure_reasons.includes('source_inventory_record_mismatch') &&
            !result.failure_reasons.includes('missing_source_inventory_record')
    );

    return {
        enriched_target_count: targets.length,
        verified_target_count: targetResults.length - blockedTargetCount,
        failed_target_count: blockedTargetCount,
        blocked_target_count: blockedTargetCount,
        source_url_evidence_complete_count: sourceUrlEvidenceCompleteCount,
        fragment_schedule_id_match_count: fragmentScheduleIdMatchCount,
        duplicate_target_id_count: countDuplicateGroups(targets.map(target => target.target_id)),
        duplicate_match_id_count: countDuplicateGroups(targets.map(target => target.match_id)),
        duplicate_source_inventory_record_key_count: countDuplicateGroups(
            targets.map(target => target.source_inventory_record_key)
        ),
        duplicate_fragment_external_id_count: countDuplicateGroups(
            targets.map(target => target.source_url_fragment_external_id)
        ),
        missing_source_page_url_count: countMissing(targets.map(target => target.source_page_url)),
        missing_source_page_url_base_count: countMissing(targets.map(target => target.source_page_url_base)),
        missing_source_url_fragment_external_id_count: countMissing(
            targets.map(target => target.source_url_fragment_external_id)
        ),
        missing_source_inventory_record_key_count: countMissing(
            targets.map(target => target.source_inventory_record_key)
        ),
        missing_schedule_date_count: missingScheduleDateCount,
        missing_schedule_home_team_count: missingScheduleHomeTeamCount,
        missing_schedule_away_team_count: missingScheduleAwayTeamCount,
        missing_required_metadata_count: missingRequiredMetadataCount,
        regeneration_status_valid_count: regenerationStatusValidCount,
        regeneration_blockers_count: regenerationBlockersCount,
        raw_write_ready_target_count: rawWriteReadyTargetCount,
        source_inventory_consistency_count: sourceInventoryConsistencyCount,
        target_results: targetResults,
        all_target_rules_passed:
            targets.length === EXPECTED_TARGET_COUNT &&
            blockedTargetCount === 0 &&
            sourceUrlEvidenceCompleteCount === EXPECTED_TARGET_COUNT &&
            fragmentScheduleIdMatchCount === EXPECTED_TARGET_COUNT &&
            regenerationStatusValidCount === EXPECTED_TARGET_COUNT &&
            regenerationBlockersCount === 0 &&
            rawWriteReadyTargetCount === 0,
    };
}

function buildRuleResults(analysis = {}, rawWriteGuardAnalysis = {}, manifest = {}) {
    return [
        ['enriched_target_count_eq_50', analysis.enriched_target_count === EXPECTED_TARGET_COUNT],
        ['source_page_url_present', analysis.missing_source_page_url_count === 0],
        ['source_page_url_base_present', analysis.missing_source_page_url_base_count === 0],
        ['source_url_fragment_external_id_present', analysis.missing_source_url_fragment_external_id_count === 0],
        ['source_inventory_record_key_present', analysis.missing_source_inventory_record_key_count === 0],
        [
            'fragment_external_id_matches_schedule_external_id',
            analysis.fragment_schedule_id_match_count === EXPECTED_TARGET_COUNT,
        ],
        ['target_id_unique', analysis.duplicate_target_id_count === 0],
        ['match_id_unique', analysis.duplicate_match_id_count === 0],
        ['source_inventory_record_key_unique', analysis.duplicate_source_inventory_record_key_count === 0],
        ['source_url_fragment_external_id_unique', analysis.duplicate_fragment_external_id_count === 0],
        ['schedule_date_present', analysis.missing_schedule_date_count === 0],
        ['schedule_home_team_present', analysis.missing_schedule_home_team_count === 0],
        ['schedule_away_team_present', analysis.missing_schedule_away_team_count === 0],
        [
            'regeneration_status_regenerated_no_write',
            analysis.regeneration_status_valid_count === EXPECTED_TARGET_COUNT,
        ],
        ['regeneration_blockers_empty', analysis.regeneration_blockers_count === 0],
        ['target_raw_write_ready_false', analysis.raw_write_ready_target_count === 0],
        ['raw_write_runner_remains_blocked', rawWriteGuardAnalysis.blocked === true],
        ['accepted_mapping_count_zero', Number(manifest.accepted_mapping_count || 0) === 0],
        ['identity_mapping_acceptance_not_performed', manifest.identity_mapping_acceptance_performed !== true],
        ['baseline_acceptance_not_performed', manifest.baseline_acceptance_performed !== true],
        ['raw_write_retry_not_performed', manifest.raw_write_retry_performed !== true],
    ].map(([rule_id, passed], index) => ({
        rule_id,
        rule_number: index + 1,
        description: VERIFICATION_RULES[index],
        passed,
    }));
}

function determineOutcome(analysis = {}, rawWriteGuardAnalysis = {}, ruleResults = []) {
    if (rawWriteGuardAnalysis.blocked !== true) {
        return {
            verification_status: 'blocked_raw_write_guard_review_required',
            ...GUARD_REVIEW_NEXT_STEP,
        };
    }
    if (analysis.all_target_rules_passed !== true || ruleResults.some(result => result.passed !== true)) {
        return {
            verification_status: 'blocked',
            ...BLOCKER_NEXT_STEP,
        };
    }
    return {
        verification_status: 'passed_no_write_source_controlled',
        ...PASS_NEXT_STEP,
    };
}

function buildArtifact({
    manifest = {},
    l2v3abPlan = {},
    l2v3aaArtifact = {},
    l2v3mArtifact = {},
    inputPathAnalysis = [],
    helperCoverage = {},
    verificationAnalysis = {},
    rawWriteGuardAnalysis = {},
    ruleResults = [],
    generatedAt = GENERATED_AT,
} = {}) {
    const outcome = determineOutcome(verificationAnalysis, rawWriteGuardAnalysis, ruleResults);
    return {
        artifact_type: 'enriched_no_write_verification_result',
        artifact_status: ARTIFACT_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        source_phase: 'Phase 5.21L2V3AB',
        generated_at: generatedAt,
        no_write: true,
        source_controlled_artifacts_only: true,
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
        verification_execution_performed: true,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        baseline_replacement_accepted: false,
        raw_write_authorization_performed: false,
        raw_write_retry_performed: false,
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
        enriched_target_count: verificationAnalysis.enriched_target_count,
        verified_target_count: verificationAnalysis.verified_target_count,
        failed_target_count: verificationAnalysis.failed_target_count,
        blocked_target_count: verificationAnalysis.blocked_target_count,
        source_url_evidence_complete_count: verificationAnalysis.source_url_evidence_complete_count,
        fragment_schedule_id_match_count: verificationAnalysis.fragment_schedule_id_match_count,
        duplicate_target_id_count: verificationAnalysis.duplicate_target_id_count,
        duplicate_match_id_count: verificationAnalysis.duplicate_match_id_count,
        duplicate_source_inventory_record_key_count: verificationAnalysis.duplicate_source_inventory_record_key_count,
        duplicate_fragment_external_id_count: verificationAnalysis.duplicate_fragment_external_id_count,
        missing_source_page_url_count: verificationAnalysis.missing_source_page_url_count,
        missing_source_page_url_base_count: verificationAnalysis.missing_source_page_url_base_count,
        missing_source_url_fragment_external_id_count:
            verificationAnalysis.missing_source_url_fragment_external_id_count,
        missing_source_inventory_record_key_count: verificationAnalysis.missing_source_inventory_record_key_count,
        missing_required_metadata_count: verificationAnalysis.missing_required_metadata_count,
        regeneration_status_valid_count: verificationAnalysis.regeneration_status_valid_count,
        regeneration_blockers_count: verificationAnalysis.regeneration_blockers_count,
        raw_write_ready_target_count: verificationAnalysis.raw_write_ready_target_count,
        raw_write_runner_blocked: rawWriteGuardAnalysis.blocked === true,
        verification_status: outcome.verification_status,
        verification_rule_count: VERIFICATION_RULES.length,
        verification_rule_results: ruleResults,
        input_analysis: inputPathAnalysis,
        helper_coverage: helperCoverage,
        verification_analysis: verificationAnalysis,
        raw_write_guard_analysis: rawWriteGuardAnalysis,
        validation_caution: {
            broad_node_test_accidental_write_path_attempt_reviewed: true,
            broad_node_test_should_not_be_used_as_regular_safety_validation: true,
            future_safety_validation_should_use_targeted_suites: true,
            accidental_write_path_attempt_blocked_by_db_constraints: true,
            cleanup_executed_after_accidental_attempt: true,
            follow_up_select_only_row_count_unchanged: true,
            protected_tables_unchanged: true,
            accidental_attempt_was_not_successful_db_write: true,
            accidental_attempt_is_not_a_pass_condition: true,
        },
        upstream_context: {
            l2v3ab_planning_status: l2v3abPlan.artifact_status || null,
            l2v3ab_verification_execution_authorization_required:
                l2v3abPlan.verification_execution_authorization_required ?? null,
            l2v3aa_regenerated_target_count: l2v3aaArtifact.regenerated_target_count ?? null,
            l2v3aa_no_write_verification_required: l2v3aaArtifact.no_write_verification_required ?? null,
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
        },
        safety_contract: {
            verification_result_is_not_accepted_mapping: true,
            verification_result_is_not_raw_write_authorization: true,
            verification_result_is_not_identity_mapping_acceptance: true,
            verification_result_is_not_baseline_acceptance: true,
            source_url_fragment_external_id_match_does_not_imply_accepted_mapping: true,
            verification_passed_does_not_imply_raw_write_ready_for_execution: true,
            raw_write_runner_remains_blocked: rawWriteGuardAnalysis.blocked === true,
            separate_identity_mapping_acceptance_required: true,
            separate_baseline_acceptance_required: true,
            separate_final_db_write_authorization_required: true,
        },
        recommended_next_step: outcome.recommended_next_step,
        next_required_step: outcome.next_required_step,
    };
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    return {
        ...manifest,
        phase_5_21_l2v3ac_execution_status: artifact.artifact_status,
        enriched_no_write_verification_execution_status: artifact.artifact_status,
        phase_5_21_l2v3ac_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3ac_report_path: REPORT_PATH,
        verification_execution_performed: true,
        live_fetch_performed: false,
        detail_fetch_performed: false,
        db_write_performed: false,
        enriched_target_count: artifact.enriched_target_count,
        verified_target_count: artifact.verified_target_count,
        failed_target_count: artifact.failed_target_count,
        blocked_target_count: artifact.blocked_target_count,
        source_url_evidence_complete_count: artifact.source_url_evidence_complete_count,
        fragment_schedule_id_match_count: artifact.fragment_schedule_id_match_count,
        raw_write_ready_target_count: 0,
        raw_write_runner_blocked: artifact.raw_write_runner_blocked,
        accepted_mapping_count: 0,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        enriched_no_write_verification_status: artifact.verification_status,
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

function buildReport(artifact = {}) {
    return `# Data Entrypoint Governance - Phase 5.21 L2V3AC

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- source_controlled_artifacts_only=true
- verification_execution_performed=true
- live_fetch_performed=false
- detail_fetch_performed=false
- db_write_performed=false
- raw_match_data_insert_performed=false
- matches_write_performed=false
- matches_external_id_modified=false
- identity_mapping_acceptance_performed=false
- baseline_acceptance_performed=false
- raw_write_retry_performed=false

## Verification Summary

- verification_status=${artifact.verification_status}
- enriched_target_count=${artifact.enriched_target_count}
- verified_target_count=${artifact.verified_target_count}
- failed_target_count=${artifact.failed_target_count}
- blocked_target_count=${artifact.blocked_target_count}
- source_url_evidence_complete_count=${artifact.source_url_evidence_complete_count}
- fragment_schedule_id_match_count=${artifact.fragment_schedule_id_match_count}
- duplicate_target_id_count=${artifact.duplicate_target_id_count}
- duplicate_match_id_count=${artifact.duplicate_match_id_count}
- duplicate_source_inventory_record_key_count=${artifact.duplicate_source_inventory_record_key_count}
- duplicate_fragment_external_id_count=${artifact.duplicate_fragment_external_id_count}
- missing_required_metadata_count=${artifact.missing_required_metadata_count}
- regeneration_status_valid_count=${artifact.regeneration_status_valid_count}
- regeneration_blockers_count=${artifact.regeneration_blockers_count}
- raw_write_ready_target_count=${artifact.raw_write_ready_target_count}
- raw_write_runner_blocked=${artifact.raw_write_runner_blocked}
- accepted_mapping_count=0
- raw_write_ready_for_execution=false

## Rule Results

${artifact.verification_rule_results
    .map(result => `- ${result.rule_number}. ${result.rule_id}: passed=${result.passed}`)
    .join('\n')}

## Input Artifacts

${artifact.input_analysis
    .map(
        item =>
            `- ${item.role}: ${item.path} (exists=${item.exists === true}, artifact=${item.count_as_artifact === true})`
    )
    .join('\n')}

## Raw Write Guard

- raw_write_guard_ok=${artifact.raw_write_guard_analysis.ok}
- raw_write_runner_blocked=${artifact.raw_write_runner_blocked}
- raw_write_guard_error_count=${artifact.raw_write_guard_analysis.error_count}
- required_next_step=${artifact.raw_write_guard_analysis.required_next_step}
- next_required_step=${artifact.raw_write_guard_analysis.next_required_step}
- write_execution_status=${artifact.raw_write_guard_analysis.write_execution_status}
- raw_match_data_write_status=${artifact.raw_write_guard_analysis.raw_match_data_write_status}

## Validation Caution

- broad node --test accidental write-path attempt reviewed=true
- broad node --test should not be used as a regular safety validation entrypoint.
- future safety validation should prefer targeted suites.
- accidental write-path attempt was blocked by DB constraints.
- cleanup executed after accidental attempt=true
- follow-up SELECT-only row count unchanged=true
- protected tables unchanged=true
- accidental attempt was not a successful DB write.
- accidental attempt is not a passing condition for this phase.

## Safety Contract

- verification result is not accepted mapping.
- verification result is not raw write authorization.
- verification result is not identity mapping acceptance.
- verification result is not baseline acceptance.
- source URL evidence match does not imply accepted mapping.
- verification passed does not imply raw_write_ready_for_execution.
- accepted_mapping_count=0 is a planning/result counter, not a DB identity acceptance state.
- raw write runner remains blocked.
- separate identity mapping acceptance is required.
- separate baseline acceptance is required.
- separate final DB-write authorization is required.

## Next Step

${artifact.recommended_next_step}
`;
}

function runEnrichedNoWriteVerificationExecution(dependencies = {}) {
    const loaded = loadDependencies(dependencies);
    const inputGate = validateInputs(
        loaded.manifest,
        loaded.l2v3abPlan,
        loaded.l2v3aaArtifact,
        loaded.l2v3aaReport,
        loaded.l2v3yArtifact,
        loaded.l2v3mArtifact
    );
    if (!inputGate.ok) return { ok: false, status: 3, errors: inputGate.errors };

    const inputPathAnalysis = analyzeInputPaths(INPUT_PATHS, dependencies);
    const helperCoverage = buildHelperCoverage(loaded.l2v3abPlan, loaded.l2v3mArtifact, dependencies);
    const verificationAnalysis = analyzeEnrichedTargets(loaded.l2v3aaArtifact, loaded.l2v3yArtifact);
    let rawWriteGuardAnalysis = buildRawWriteGuardAnalysis(loaded.manifest, dependencies);
    let ruleResults = buildRuleResults(verificationAnalysis, rawWriteGuardAnalysis, loaded.manifest);
    let artifact = buildArtifact({
        manifest: loaded.manifest,
        l2v3abPlan: loaded.l2v3abPlan,
        l2v3aaArtifact: loaded.l2v3aaArtifact,
        l2v3mArtifact: loaded.l2v3mArtifact,
        inputPathAnalysis,
        helperCoverage,
        verificationAnalysis,
        rawWriteGuardAnalysis,
        ruleResults,
        generatedAt: dependencies.generatedAt || GENERATED_AT,
    });
    let updatedManifest = updateManifestMetadata(loaded.manifest, artifact);
    rawWriteGuardAnalysis = buildRawWriteGuardAnalysis(updatedManifest, dependencies);
    ruleResults = buildRuleResults(verificationAnalysis, rawWriteGuardAnalysis, updatedManifest);
    artifact = buildArtifact({
        manifest: updatedManifest,
        l2v3abPlan: loaded.l2v3abPlan,
        l2v3aaArtifact: loaded.l2v3aaArtifact,
        l2v3mArtifact: loaded.l2v3mArtifact,
        inputPathAnalysis,
        helperCoverage,
        verificationAnalysis,
        rawWriteGuardAnalysis,
        ruleResults,
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
        '  node scripts/ops/pageprops_v2_enriched_no_write_verification_execute.js --write-files=yes',
        '',
        'Safety:',
        '  L2V3AC is a controlled enriched no-write verification execution phase.',
        '  It only reads source-controlled artifacts and does not live fetch, detail fetch, write DB/raw/matches, accept mappings, accept baselines, or retry raw writes.',
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
    const result = runEnrichedNoWriteVerificationExecution({ writeFiles: options.writeFiles });
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
                verification_execution_performed: result.artifact.verification_execution_performed,
                live_fetch_performed: result.artifact.live_fetch_performed,
                detail_fetch_performed: result.artifact.detail_fetch_performed,
                db_write_performed: result.artifact.db_write_performed,
                enriched_target_count: result.artifact.enriched_target_count,
                verified_target_count: result.artifact.verified_target_count,
                failed_target_count: result.artifact.failed_target_count,
                blocked_target_count: result.artifact.blocked_target_count,
                raw_write_ready_target_count: result.artifact.raw_write_ready_target_count,
                raw_write_runner_blocked: result.artifact.raw_write_runner_blocked,
                accepted_mapping_count: result.artifact.accepted_mapping_count,
                raw_write_ready_for_execution: result.artifact.raw_write_ready_for_execution,
                verification_status: result.artifact.verification_status,
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
    L2V3AB_PLAN_PATH,
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
    buildRuleResults,
    buildRawWriteGuardAnalysis,
    buildArtifact,
    updateManifestMetadata,
    buildReport,
    runEnrichedNoWriteVerificationExecution,
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
