#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3Z';
const PHASE_NAME = 'enriched_target_regeneration_planning';
const ARTIFACT_STATUS = 'completed_no_write_enriched_target_regeneration_planning';
const GENERATED_AT = '2026-05-21T15:30:00Z';
const MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const L2V3Y_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.controlled_source_inventory_acquisition_result.phase521l2v3y.json';
const L2V3X_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.controlled_source_inventory_acquisition_plan.phase521l2v3x.json';
const L2V3W_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.source_inventory_acquisition_path_investigation.phase521l2v3w.json';
const L2V3V_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.source_inventory_enrichment_implementation.phase521l2v3v.json';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_target_regeneration_plan.phase521l2v3z.json';
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3Z.md';
const PLANNED_REGENERATION_SCOPE =
    'phase521l2v3y_current_50_candidates_enriched_target_regeneration_planning_from_metadata_only_source_inventory';
const CONTINUE_PLANNING_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AA: continued enriched target regeneration planning',
    next_required_step: 'continued_enriched_target_regeneration_planning',
});
const HELPER_IMPLEMENTATION_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AA: enriched target regeneration helper implementation',
    next_required_step: 'enriched_target_regeneration_helper_implementation',
});
const EXECUTION_STEP = Object.freeze({
    recommended_next_step: 'Phase 5.21L2V3AA: controlled enriched target regeneration execution',
    next_required_step: 'controlled_enriched_target_regeneration_execution',
});
const HELPER_PATHS = Object.freeze({
    source_inventory_adapter: 'src/infrastructure/services/FotMobSourceInventoryAdapter.js',
    manifest_candidate_builder: 'scripts/ops/single_league_small_batch_target_manifest_plan.js',
    source_inventory_enrichment_apply: 'scripts/ops/pageprops_v2_source_inventory_enrichment_apply.js',
    no_write_preview_helper: 'scripts/ops/pageprops_v2_no_write_preview.js',
});
const INPUT_PATHS = Object.freeze([
    { key: 'manifest', path: MANIFEST_PATH, role: 'current_manifest' },
    { key: 'l2v3y_artifact', path: L2V3Y_ARTIFACT_PATH, role: 'controlled_source_inventory_acquisition_result' },
    { key: 'l2v3y_report', path: 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3Y.md', role: 'report' },
    { key: 'l2v3x_artifact', path: L2V3X_ARTIFACT_PATH, role: 'controlled_source_inventory_acquisition_plan' },
    { key: 'l2v3x_report', path: 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3X.md', role: 'report' },
    { key: 'l2v3w_artifact', path: L2V3W_ARTIFACT_PATH, role: 'source_inventory_acquisition_path_investigation' },
    { key: 'l2v3w_report', path: 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3W.md', role: 'report' },
    { key: 'l2v3v_artifact', path: L2V3V_ARTIFACT_PATH, role: 'source_inventory_enrichment_implementation' },
    { key: 'l2v3v_report', path: 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3V.md', role: 'report' },
    {
        key: 'source_inventory_adapter',
        path: HELPER_PATHS.source_inventory_adapter,
        role: 'source_inventory_adapter',
    },
    {
        key: 'manifest_candidate_builder',
        path: HELPER_PATHS.manifest_candidate_builder,
        role: 'manifest_candidate_builder',
    },
    {
        key: 'source_inventory_enrichment_apply',
        path: HELPER_PATHS.source_inventory_enrichment_apply,
        role: 'source_inventory_enrichment_helper',
    },
    {
        key: 'no_write_preview_helper',
        path: HELPER_PATHS.no_write_preview_helper,
        role: 'no_write_preview_helper',
    },
    {
        key: 'l2v3y_test',
        path: 'tests/unit/pageprops_v2_controlled_source_inventory_acquisition_execute.test.js',
        role: 'relevant_test',
    },
    {
        key: 'source_inventory_reconciliation_test',
        path: 'tests/unit/pageprops_v2_target_source_inventory_reconciliation_plan.test.js',
        role: 'relevant_test',
    },
]);
const PLANNED_ENRICHED_FIELDS = Object.freeze([
    {
        field: 'target_id',
        purpose: 'stable current manifest candidate identity used as the primary regeneration mapping key',
    },
    {
        field: 'match_id',
        purpose: 'stable match identity cross-check against the current manifest candidate target',
    },
    {
        field: 'external_id',
        purpose: 'current candidate external id retained for downstream checks and existing selectors',
    },
    {
        field: 'schedule_external_id',
        purpose: 'requested schedule-side external id captured from source inventory metadata',
    },
    {
        field: 'source_page_url',
        purpose: 'requested-side source inventory page URL captured during L2V3Y acquisition',
    },
    {
        field: 'source_page_url_base',
        purpose: 'requested-side source page URL without fragment for future route/slug verification',
    },
    {
        field: 'source_url_fragment_external_id',
        purpose: 'fragment anchor external id cross-check against schedule_external_id',
    },
    {
        field: 'source_slug',
        purpose: 'slug segment parsed from source_page_url for future no-write verification',
    },
    {
        field: 'source_route_code',
        purpose: 'route code segment parsed from source_page_url for future no-write verification',
    },
    {
        field: 'schedule_date',
        purpose: 'requested schedule-side kickoff timestamp cross-check carried into regenerated targets',
    },
    {
        field: 'schedule_home_team',
        purpose: 'requested schedule-side home team cross-check carried into regenerated targets',
    },
    {
        field: 'schedule_away_team',
        purpose: 'requested schedule-side away team cross-check carried into regenerated targets',
    },
    {
        field: 'source_inventory_record_key',
        purpose: 'deterministic per-record source inventory key used as a uniqueness guard and audit field',
    },
    {
        field: 'source_inventory_generated_at',
        purpose: 'timestamp of the L2V3Y authorized source inventory acquisition run',
    },
    {
        field: 'identity_evidence_status',
        purpose: 'source inventory evidence classification; complete does not imply accepted mapping',
    },
    {
        field: 'enrichment_source_artifact',
        purpose: 'source-controlled artifact path proving which L2V3Y acquisition result fed regeneration',
    },
    {
        field: 'regeneration_status',
        purpose: 'explicit regeneration lifecycle marker distinct from accepted mapping or raw write status',
    },
    {
        field: 'raw_write_ready_for_execution',
        purpose: 'must remain false after regeneration planning and after future regeneration execution',
    },
]);
const VALIDATION_RULES = Object.freeze([
    '50 candidates must map one-to-one to 50 acquired source records.',
    'target_id is the planned primary mapping key; match_id, schedule_external_id, and source_url_fragment_external_id are required cross-check keys.',
    'source_url_fragment_external_id should match schedule_external_id, or block.',
    'source_page_url_base present, or block.',
    'source_inventory_record_key present, or block.',
    'duplicate source_inventory_record_key blocks.',
    'duplicate source_url_fragment_external_id blocks.',
    'missing schedule/team/date metadata blocks.',
    'acquired metadata does not imply accepted mapping.',
    'identity_evidence_complete does not imply raw_write_ready_for_execution.',
    'regenerated targets must keep accepted_mapping_count=0 and raw_write_ready_for_execution=false.',
]);
const NO_WRITE_VERIFICATION_PLAN = Object.freeze([
    'Run a separate no-write enriched verification phase after regeneration execution.',
    'Verify regenerated enriched targets retain source_page_url/source_page_url_base/source_url_fragment_external_id/source_inventory_record_key for all 50 candidates.',
    'Compare source-side requested metadata against observed detail-side identity in a separate no-write verification phase.',
    'Confirm the raw write runner still rejects the manifest after regeneration until identity mapping acceptance, baseline acceptance, and final DB-write authorization complete separately.',
    'Confirm no full raw_data, pageProps, HTML, or source body is saved or printed in the regeneration artifact, report, or manifest.',
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

function analyzeInputPaths(paths = [], dependencies = {}) {
    return paths.map(item => {
        if (dependencies.inputPathAnalysisByPath && dependencies.inputPathAnalysisByPath[item.path]) {
            return {
                key: item.key,
                path: item.path,
                role: item.role,
                ...dependencies.inputPathAnalysisByPath[item.path],
            };
        }
        return {
            key: item.key,
            path: item.path,
            role: item.role,
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

function buildHelperCoverage(dependencies = {}) {
    const adapterText = readImplementationText(HELPER_PATHS.source_inventory_adapter, dependencies);
    const manifestBuilderText = readImplementationText(HELPER_PATHS.manifest_candidate_builder, dependencies);
    const enrichmentHelperText = readImplementationText(HELPER_PATHS.source_inventory_enrichment_apply, dependencies);
    const previewText = readImplementationText(HELPER_PATHS.no_write_preview_helper, dependencies);

    return {
        source_inventory_adapter_extracts_identity_evidence:
            adapterText.includes('deriveSourceInventoryIdentityEvidence') &&
            adapterText.includes('source_page_url_base') &&
            adapterText.includes('source_inventory_record_key'),
        manifest_builder_schema_includes_required_fields:
            manifestBuilderText.includes('source_page_url') &&
            manifestBuilderText.includes('source_inventory_record_key') &&
            manifestBuilderText.includes('identity_evidence_status'),
        source_inventory_enrichment_helper_present:
            enrichmentHelperText.includes('enrichCandidateTarget') &&
            enrichmentHelperText.includes('source_url_fragment_external_id') &&
            enrichmentHelperText.includes('identity_evidence_status'),
        no_write_preview_helper_available:
            previewText.includes('validatePreviewInput') && previewText.includes('allow-db-write'),
        checked_paths: Object.values(HELPER_PATHS),
    };
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

function analyzeMapping(manifest = {}, l2v3yArtifact = {}) {
    const candidates = Array.isArray(manifest.candidate_targets) ? manifest.candidate_targets : [];
    const records = Array.isArray(l2v3yArtifact.source_inventory_metadata_records)
        ? l2v3yArtifact.source_inventory_metadata_records
        : [];
    const candidateByTargetId = new Map(candidates.map(candidate => [normalizeText(candidate.target_id), candidate]));
    const candidateByMatchId = new Map(candidates.map(candidate => [normalizeText(candidate.match_id), candidate]));
    const candidateByExternalId = new Map(
        candidates.map(candidate => [normalizeText(candidate.external_id || candidate.schedule_external_id), candidate])
    );
    const duplicateTargetIdCount = countDuplicates(records.map(record => record.target_id));
    const duplicateMatchIdCount = countDuplicates(records.map(record => record.match_id));
    const duplicateScheduleExternalIdCount = countDuplicates(records.map(record => record.schedule_external_id));
    const duplicateFragmentExternalIdCount = countDuplicates(
        records.map(record => record.source_url_fragment_external_id)
    );
    const duplicateSourceRecordKeyCount = countDuplicates(records.map(record => record.source_inventory_record_key));
    const missingSourcePageUrlCount = countMissing(records.map(record => record.source_page_url));
    const missingSourcePageUrlBaseCount = countMissing(records.map(record => record.source_page_url_base));
    const missingFragmentExternalIdCount = countMissing(records.map(record => record.source_url_fragment_external_id));
    const missingSourceRecordKeyCount = countMissing(records.map(record => record.source_inventory_record_key));
    const missingScheduleMetadataCount = countWhere(
        records,
        record =>
            !normalizeText(record.schedule_external_id) ||
            !normalizeText(record.schedule_date) ||
            !normalizeText(record.schedule_home_team) ||
            !normalizeText(record.schedule_away_team)
    );
    const targetIdExactMatchCount = countWhere(records, record =>
        candidateByTargetId.has(normalizeText(record.target_id))
    );
    const matchIdExactMatchCount = countWhere(records, record =>
        candidateByMatchId.has(normalizeText(record.match_id))
    );
    const scheduleExternalIdExactMatchCount = countWhere(records, record =>
        candidateByExternalId.has(normalizeText(record.schedule_external_id))
    );
    const fragmentExternalIdExactMatchCount = countWhere(records, record =>
        candidateByExternalId.has(normalizeText(record.source_url_fragment_external_id))
    );
    const scheduleMetadataExactMatchCount = countWhere(records, record => {
        const candidate = candidateByTargetId.get(normalizeText(record.target_id));
        if (!candidate) return false;
        return (
            normalizeText(candidate.external_id) === normalizeText(record.schedule_external_id) &&
            normalizeText(candidate.kickoff_time || candidate.match_date) === normalizeText(record.schedule_date) &&
            normalizeText(candidate.home_team) === normalizeText(record.schedule_home_team) &&
            normalizeText(candidate.away_team) === normalizeText(record.schedule_away_team)
        );
    });
    const plannedMappingKey =
        targetIdExactMatchCount === records.length && duplicateTargetIdCount === 0 && records.length > 0
            ? 'target_id'
            : matchIdExactMatchCount === records.length && duplicateMatchIdCount === 0 && records.length > 0
              ? 'match_id'
              : scheduleExternalIdExactMatchCount === records.length &&
                  duplicateScheduleExternalIdCount === 0 &&
                  records.length > 0
                ? 'schedule_external_id'
                : 'unknown';
    const oneToOneMappingExpected =
        candidates.length === 50 &&
        records.length === 50 &&
        duplicateTargetIdCount === 0 &&
        duplicateMatchIdCount === 0 &&
        duplicateScheduleExternalIdCount === 0 &&
        duplicateFragmentExternalIdCount === 0 &&
        duplicateSourceRecordKeyCount === 0 &&
        missingSourcePageUrlCount === 0 &&
        missingSourcePageUrlBaseCount === 0 &&
        missingFragmentExternalIdCount === 0 &&
        missingSourceRecordKeyCount === 0 &&
        missingScheduleMetadataCount === 0 &&
        targetIdExactMatchCount === 50 &&
        matchIdExactMatchCount === 50 &&
        scheduleExternalIdExactMatchCount === 50 &&
        fragmentExternalIdExactMatchCount === 50 &&
        scheduleMetadataExactMatchCount === 50;
    const blockingReasons = [];
    if (plannedMappingKey === 'unknown') blockingReasons.push('planned_mapping_key_unknown');
    if (duplicateTargetIdCount > 0) blockingReasons.push('duplicate_target_id_detected');
    if (duplicateMatchIdCount > 0) blockingReasons.push('duplicate_match_id_detected');
    if (duplicateScheduleExternalIdCount > 0) blockingReasons.push('duplicate_schedule_external_id_detected');
    if (duplicateFragmentExternalIdCount > 0) {
        blockingReasons.push('duplicate_source_url_fragment_external_id_detected');
    }
    if (duplicateSourceRecordKeyCount > 0) blockingReasons.push('duplicate_source_inventory_record_key_detected');
    if (missingSourcePageUrlCount > 0) blockingReasons.push('missing_source_page_url_detected');
    if (missingSourcePageUrlBaseCount > 0) blockingReasons.push('missing_source_page_url_base_detected');
    if (missingFragmentExternalIdCount > 0) blockingReasons.push('missing_source_url_fragment_external_id_detected');
    if (missingSourceRecordKeyCount > 0) blockingReasons.push('missing_source_inventory_record_key_detected');
    if (missingScheduleMetadataCount > 0) blockingReasons.push('missing_schedule_metadata_detected');
    if (targetIdExactMatchCount !== records.length) blockingReasons.push('target_id_match_count_incomplete');
    if (matchIdExactMatchCount !== records.length) blockingReasons.push('match_id_match_count_incomplete');
    if (scheduleExternalIdExactMatchCount !== records.length) {
        blockingReasons.push('schedule_external_id_match_count_incomplete');
    }
    if (fragmentExternalIdExactMatchCount !== records.length) {
        blockingReasons.push('source_url_fragment_external_id_match_count_incomplete');
    }
    if (scheduleMetadataExactMatchCount !== records.length) {
        blockingReasons.push('schedule_metadata_cross_check_incomplete');
    }

    return {
        candidate_scope_count: candidates.length,
        acquired_source_record_count: records.length,
        planned_mapping_key: plannedMappingKey,
        planned_cross_check_keys: ['match_id', 'schedule_external_id', 'source_url_fragment_external_id'],
        source_inventory_record_key_usage: 'uniqueness_guard_and_persistence_field',
        one_to_one_mapping_expected: oneToOneMappingExpected,
        duplicate_target_id_count: duplicateTargetIdCount,
        duplicate_match_id_count: duplicateMatchIdCount,
        duplicate_schedule_external_id_count: duplicateScheduleExternalIdCount,
        duplicate_fragment_external_id_count: duplicateFragmentExternalIdCount,
        duplicate_source_record_key_count: duplicateSourceRecordKeyCount,
        missing_source_page_url_count: missingSourcePageUrlCount,
        missing_source_page_url_base_count: missingSourcePageUrlBaseCount,
        missing_source_url_fragment_external_id_count: missingFragmentExternalIdCount,
        missing_source_inventory_record_key_count: missingSourceRecordKeyCount,
        missing_schedule_metadata_count: missingScheduleMetadataCount,
        target_id_exact_match_count: targetIdExactMatchCount,
        match_id_exact_match_count: matchIdExactMatchCount,
        schedule_external_id_exact_match_count: scheduleExternalIdExactMatchCount,
        source_url_fragment_external_id_exact_match_count: fragmentExternalIdExactMatchCount,
        schedule_metadata_exact_match_count: scheduleMetadataExactMatchCount,
        blocking_reasons: blockingReasons,
    };
}

function validateInputs(manifest = {}, l2v3yArtifact = {}, l2v3xArtifact = {}, l2v3wArtifact = {}, l2v3vArtifact = {}) {
    const errors = [];
    const alreadyCompleted =
        normalizeText(manifest.phase_5_21_l2v3z_planning_status) === ARTIFACT_STATUS &&
        normalizeText(manifest.enriched_target_regeneration_planning_status) === ARTIFACT_STATUS;
    if (normalizeText(manifest.next_required_step) !== 'enriched_target_regeneration_planning' && !alreadyCompleted) {
        errors.push('manifest next_required_step must be enriched_target_regeneration_planning');
    }
    if (!Array.isArray(manifest.candidate_targets) || manifest.candidate_targets.length !== 50) {
        errors.push('manifest candidate_targets must contain 50 targets');
    }
    if (manifest.raw_write_ready_for_execution !== false) {
        errors.push('manifest raw_write_ready_for_execution must remain false');
    }
    if (Number(manifest.accepted_mapping_count || 0) !== 0) {
        errors.push('manifest accepted_mapping_count must remain 0');
    }
    if (normalizeText(l2v3yArtifact.proposal_phase) !== 'Phase 5.21L2V3Y') {
        errors.push('L2V3Y artifact must be present');
    }
    if (l2v3yArtifact.live_fetch_performed !== true) {
        errors.push('L2V3Y live_fetch_performed must be true');
    }
    if (l2v3yArtifact.db_write_performed !== false) {
        errors.push('L2V3Y db_write_performed must remain false');
    }
    if (normalizeText(l2v3yArtifact.endpoint_used) !== '/api/data/leagues?id=53&season=20252026') {
        errors.push('L2V3Y endpoint_used must match the controlled source inventory endpoint');
    }
    if (Number(l2v3yArtifact.candidate_scope_count || 0) !== 50) {
        errors.push('L2V3Y candidate_scope_count must be 50');
    }
    if (Number(l2v3yArtifact.candidate_targets_matched_count || 0) !== 50) {
        errors.push('L2V3Y candidate_targets_matched_count must be 50');
    }
    if (Number(l2v3yArtifact.candidate_targets_with_source_page_url || 0) !== 50) {
        errors.push('L2V3Y candidate_targets_with_source_page_url must be 50');
    }
    if (Number(l2v3yArtifact.candidate_targets_with_source_page_url_base || 0) !== 50) {
        errors.push('L2V3Y candidate_targets_with_source_page_url_base must be 50');
    }
    if (Number(l2v3yArtifact.candidate_targets_with_source_url_fragment_external_id || 0) !== 50) {
        errors.push('L2V3Y candidate_targets_with_source_url_fragment_external_id must be 50');
    }
    if (Number(l2v3yArtifact.candidate_targets_with_source_inventory_record_key || 0) !== 50) {
        errors.push('L2V3Y candidate_targets_with_source_inventory_record_key must be 50');
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
    if (normalizeText(l2v3xArtifact.proposal_phase) !== 'Phase 5.21L2V3X') {
        errors.push('L2V3X artifact must be present');
    }
    if (normalizeText(l2v3xArtifact.planned_source_endpoint) !== '/api/data/leagues?id=53&season=20252026') {
        errors.push('L2V3X planned_source_endpoint must match the controlled source inventory endpoint');
    }
    if (Number(l2v3xArtifact.planned_candidate_scope_count || 0) !== 50) {
        errors.push('L2V3X planned_candidate_scope_count must be 50');
    }
    if (l2v3xArtifact.raw_write_ready_for_execution !== false) {
        errors.push('L2V3X raw_write_ready_for_execution must remain false');
    }
    if (Number(l2v3xArtifact.accepted_mapping_count || 0) !== 0) {
        errors.push('L2V3X accepted_mapping_count must remain 0');
    }
    if (normalizeText(l2v3wArtifact.proposal_phase) !== 'Phase 5.21L2V3W') {
        errors.push('L2V3W artifact must be present');
    }
    if (l2v3wArtifact.requires_source_inventory_regeneration !== true) {
        errors.push('L2V3W requires_source_inventory_regeneration must remain true');
    }
    if (normalizeText(l2v3vArtifact.proposal_phase) !== 'Phase 5.21L2V3V') {
        errors.push('L2V3V artifact must be present');
    }
    if (l2v3vArtifact.raw_write_ready_for_execution !== false) {
        errors.push('L2V3V raw_write_ready_for_execution must remain false');
    }
    if (Number(l2v3vArtifact.accepted_mapping_count || 0) !== 0) {
        errors.push('L2V3V accepted_mapping_count must remain 0');
    }
    return { ok: errors.length === 0, errors };
}

function determineNextStep(mappingAnalysis = {}, helperCoverage = {}) {
    if (
        helperCoverage.source_inventory_adapter_extracts_identity_evidence !== true ||
        helperCoverage.manifest_builder_schema_includes_required_fields !== true ||
        helperCoverage.source_inventory_enrichment_helper_present !== true
    ) {
        return HELPER_IMPLEMENTATION_STEP;
    }
    if (
        mappingAnalysis.planned_mapping_key === 'unknown' ||
        mappingAnalysis.one_to_one_mapping_expected !== true ||
        mappingAnalysis.blocking_reasons.length > 0
    ) {
        return CONTINUE_PLANNING_STEP;
    }
    return EXECUTION_STEP;
}

function buildArtifact({
    manifest = {},
    l2v3yArtifact = {},
    l2v3xArtifact = {},
    l2v3wArtifact = {},
    l2v3vArtifact = {},
    inputPathAnalysis = [],
    helperCoverage = {},
    mappingAnalysis = {},
    generatedAt = GENERATED_AT,
} = {}) {
    const nextStep = determineNextStep(mappingAnalysis, helperCoverage);
    return {
        artifact_type: 'enriched_target_regeneration_plan',
        artifact_status: ARTIFACT_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        source_phase: 'Phase 5.21L2V3Y',
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
        target_regeneration_execution_performed: false,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        baseline_replacement_accepted: false,
        raw_write_authorization_performed: false,
        raw_write_retry_performed: false,
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
        planned_regeneration_scope: PLANNED_REGENERATION_SCOPE,
        candidate_scope_count: mappingAnalysis.candidate_scope_count,
        acquired_source_record_count: mappingAnalysis.acquired_source_record_count,
        planned_mapping_key: mappingAnalysis.planned_mapping_key,
        planned_cross_check_keys: mappingAnalysis.planned_cross_check_keys,
        one_to_one_mapping_expected: mappingAnalysis.one_to_one_mapping_expected,
        duplicate_source_record_key_count: mappingAnalysis.duplicate_source_record_key_count,
        duplicate_fragment_external_id_count: mappingAnalysis.duplicate_fragment_external_id_count,
        missing_source_page_url_count: mappingAnalysis.missing_source_page_url_count,
        missing_source_page_url_base_count: mappingAnalysis.missing_source_page_url_base_count,
        missing_source_url_fragment_external_id_count: mappingAnalysis.missing_source_url_fragment_external_id_count,
        missing_source_inventory_record_key_count: mappingAnalysis.missing_source_inventory_record_key_count,
        missing_schedule_metadata_count: mappingAnalysis.missing_schedule_metadata_count,
        planned_enriched_field_count: PLANNED_ENRICHED_FIELDS.length,
        regeneration_execution_authorization_required: true,
        no_write_verification_required: true,
        planned_enriched_fields: PLANNED_ENRICHED_FIELDS,
        validation_rules: VALIDATION_RULES,
        no_write_verification_plan: NO_WRITE_VERIFICATION_PLAN,
        input_analysis: inputPathAnalysis,
        helper_coverage: helperCoverage,
        mapping_analysis: mappingAnalysis,
        upstream_context: {
            l2v3y_candidate_targets_matched_count: l2v3yArtifact.candidate_targets_matched_count ?? null,
            l2v3y_identity_evidence_complete_count: l2v3yArtifact.identity_evidence_complete_count ?? null,
            l2v3x_planned_metadata_field_count: l2v3xArtifact.planned_metadata_field_count ?? null,
            l2v3w_requires_source_inventory_regeneration: l2v3wArtifact.requires_source_inventory_regeneration ?? null,
            l2v3v_manifest_candidate_builder_updated: l2v3vArtifact.manifest_candidate_builder_updated ?? null,
            current_manifest_next_required_step: manifest.next_required_step || null,
        },
        safety_contract: {
            enriched_target_regeneration_plan_is_not_accepted_mapping: true,
            enriched_target_regeneration_plan_is_not_raw_write_authorization: true,
            enriched_target_regeneration_plan_is_not_identity_mapping_acceptance: true,
            enriched_target_regeneration_plan_is_not_baseline_acceptance: true,
            enriched_target_regeneration_plan_is_not_raw_write_retry: true,
            acquired_source_url_evidence_does_not_imply_accepted_mapping: true,
            identity_evidence_complete_does_not_imply_raw_write_ready_for_execution: true,
            regeneration_execution_requires_separate_authorization: true,
            no_write_verification_remains_required: true,
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
        phase_5_21_l2v3z_planning_status: artifact.artifact_status,
        enriched_target_regeneration_planning_status: artifact.artifact_status,
        phase_5_21_l2v3z_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3z_report_path: REPORT_PATH,
        planned_regeneration_scope: artifact.planned_regeneration_scope,
        phase_5_21_l2v3z_planned_regeneration_scope: artifact.planned_regeneration_scope,
        candidate_scope_count: artifact.candidate_scope_count,
        phase_5_21_l2v3z_candidate_scope_count: artifact.candidate_scope_count,
        acquired_source_record_count: artifact.acquired_source_record_count,
        phase_5_21_l2v3z_acquired_source_record_count: artifact.acquired_source_record_count,
        planned_mapping_key: artifact.planned_mapping_key,
        phase_5_21_l2v3z_planned_mapping_key: artifact.planned_mapping_key,
        one_to_one_mapping_expected: artifact.one_to_one_mapping_expected,
        phase_5_21_l2v3z_one_to_one_mapping_expected: artifact.one_to_one_mapping_expected,
        duplicate_source_record_key_count: artifact.duplicate_source_record_key_count,
        phase_5_21_l2v3z_duplicate_source_record_key_count: artifact.duplicate_source_record_key_count,
        duplicate_fragment_external_id_count: artifact.duplicate_fragment_external_id_count,
        phase_5_21_l2v3z_duplicate_fragment_external_id_count: artifact.duplicate_fragment_external_id_count,
        missing_source_page_url_count: artifact.missing_source_page_url_count,
        phase_5_21_l2v3z_missing_source_page_url_count: artifact.missing_source_page_url_count,
        missing_source_page_url_base_count: artifact.missing_source_page_url_base_count,
        phase_5_21_l2v3z_missing_source_page_url_base_count: artifact.missing_source_page_url_base_count,
        missing_source_url_fragment_external_id_count: artifact.missing_source_url_fragment_external_id_count,
        phase_5_21_l2v3z_missing_source_url_fragment_external_id_count:
            artifact.missing_source_url_fragment_external_id_count,
        missing_source_inventory_record_key_count: artifact.missing_source_inventory_record_key_count,
        phase_5_21_l2v3z_missing_source_inventory_record_key_count: artifact.missing_source_inventory_record_key_count,
        planned_enriched_field_count: artifact.planned_enriched_field_count,
        phase_5_21_l2v3z_planned_enriched_field_count: artifact.planned_enriched_field_count,
        regeneration_execution_authorization_required: true,
        phase_5_21_l2v3z_regeneration_execution_authorization_required: true,
        no_write_verification_required: true,
        phase_5_21_l2v3z_no_write_verification_required: true,
        accepted_mapping_count: 0,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        phase_5_21_l2v3z_accepted_mapping_count: 0,
        phase_5_21_l2v3z_identity_mapping_acceptance_performed: false,
        phase_5_21_l2v3z_baseline_acceptance_performed: false,
        phase_5_21_l2v3z_raw_write_retry_performed: false,
        phase_5_21_l2v3z_raw_write_ready_for_execution: false,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

function buildReport(artifact = {}) {
    return `# Data Entrypoint Governance - Phase 5.21 L2V3Z

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- no_write=true
- live_fetch_performed=false
- network_request_performed=false
- db_write_performed=false
- raw_match_data_insert_performed=false
- matches_write_performed=false
- matches_external_id_modified=false
- schema_migration_performed=false
- parser_features_training_prediction_performed=false
- browser_proxy_captcha_bypass_performed=false
- target_regeneration_execution_performed=false

## Classification Output

- planned_regeneration_scope=${artifact.planned_regeneration_scope}
- candidate_scope_count=${artifact.candidate_scope_count}
- acquired_source_record_count=${artifact.acquired_source_record_count}
- planned_mapping_key=${artifact.planned_mapping_key}
- one_to_one_mapping_expected=${artifact.one_to_one_mapping_expected}
- duplicate_source_record_key_count=${artifact.duplicate_source_record_key_count}
- duplicate_fragment_external_id_count=${artifact.duplicate_fragment_external_id_count}
- missing_source_page_url_count=${artifact.missing_source_page_url_count}
- missing_source_page_url_base_count=${artifact.missing_source_page_url_base_count}
- missing_source_url_fragment_external_id_count=${artifact.missing_source_url_fragment_external_id_count}
- missing_source_inventory_record_key_count=${artifact.missing_source_inventory_record_key_count}
- missing_schedule_metadata_count=${artifact.missing_schedule_metadata_count}
- planned_enriched_field_count=${artifact.planned_enriched_field_count}
- regeneration_execution_authorization_required=true
- no_write_verification_required=true
- accepted_mapping_count=0
- raw_write_ready_for_execution=false

## Planned Mapping

- primary_mapping_key=${artifact.planned_mapping_key}
- cross_check_keys=${artifact.planned_cross_check_keys.join(', ')}
- source_inventory_record_key_usage=${artifact.mapping_analysis.source_inventory_record_key_usage}
- target_id_exact_match_count=${artifact.mapping_analysis.target_id_exact_match_count}
- match_id_exact_match_count=${artifact.mapping_analysis.match_id_exact_match_count}
- schedule_external_id_exact_match_count=${artifact.mapping_analysis.schedule_external_id_exact_match_count}
- source_url_fragment_external_id_exact_match_count=${artifact.mapping_analysis.source_url_fragment_external_id_exact_match_count}
- schedule_metadata_exact_match_count=${artifact.mapping_analysis.schedule_metadata_exact_match_count}

The current L2V3Y artifact already preserves current-candidate identity through target_id and match_id on all 50 records. The plan therefore uses target_id as the primary regeneration mapping key, with match_id, schedule_external_id, and source_url_fragment_external_id required as independent cross-checks. source_inventory_record_key is preserved as an enriched evidence field and uniqueness guard, not as the sole mapping key back to the current manifest.

## Planned Enriched Fields

${artifact.planned_enriched_fields.map(item => `- ${item.field}: ${item.purpose}`).join('\n')}

## Validation Rules

${artifact.validation_rules.map(item => `- ${item}`).join('\n')}

## No-Write Verification Plan

${artifact.no_write_verification_plan.map(item => `- ${item}`).join('\n')}

## Safety Contract

- enriched target regeneration plan is not accepted mapping.
- enriched target regeneration plan is not raw write authorization.
- enriched target regeneration plan is not identity mapping acceptance.
- enriched target regeneration plan is not baseline acceptance.
- enriched target regeneration plan is not raw write retry.
- acquired source URL evidence does not imply accepted mapping.
- identity_evidence_complete does not imply raw_write_ready_for_execution.
- regeneration execution requires separate authorization.
- no-write verification remains required.
- separate identity mapping acceptance is required.
- separate baseline acceptance is required.
- separate final DB-write authorization is required.

## Next Step

${artifact.recommended_next_step}
`;
}

function loadDependencies(dependencies = {}) {
    return {
        manifest: dependencies.manifest || readJsonFile(MANIFEST_PATH),
        l2v3yArtifact: dependencies.l2v3yArtifact || readJsonFile(L2V3Y_ARTIFACT_PATH),
        l2v3xArtifact: dependencies.l2v3xArtifact || readJsonFile(L2V3X_ARTIFACT_PATH),
        l2v3wArtifact: dependencies.l2v3wArtifact || readJsonFile(L2V3W_ARTIFACT_PATH),
        l2v3vArtifact: dependencies.l2v3vArtifact || readJsonFile(L2V3V_ARTIFACT_PATH),
    };
}

function runEnrichedTargetRegenerationPlan(dependencies = {}) {
    const loaded = loadDependencies(dependencies);
    const inputGate = validateInputs(
        loaded.manifest,
        loaded.l2v3yArtifact,
        loaded.l2v3xArtifact,
        loaded.l2v3wArtifact,
        loaded.l2v3vArtifact
    );
    if (!inputGate.ok) return { ok: false, status: 3, errors: inputGate.errors };

    const inputPathAnalysis = analyzeInputPaths(INPUT_PATHS, dependencies);
    const helperCoverage = buildHelperCoverage(dependencies);
    const mappingAnalysis = analyzeMapping(loaded.manifest, loaded.l2v3yArtifact);
    const artifact = buildArtifact({
        ...loaded,
        inputPathAnalysis,
        helperCoverage,
        mappingAnalysis,
        generatedAt: dependencies.generatedAt || GENERATED_AT,
    });
    const updatedManifest = updateManifestMetadata(loaded.manifest, artifact);
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
        '  node scripts/ops/pageprops_v2_enriched_target_regeneration_plan.js --write-files=yes',
        '',
        'Safety:',
        '  L2V3Z is a no-write enriched target regeneration planning phase.',
        '  It does not live fetch, regenerate targets, write DB/raw/matches, accept mappings, accept baselines, or retry raw writes.',
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
    const result = runEnrichedTargetRegenerationPlan({ writeFiles: options.writeFiles });
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
                planned_regeneration_scope: result.artifact.planned_regeneration_scope,
                candidate_scope_count: result.artifact.candidate_scope_count,
                acquired_source_record_count: result.artifact.acquired_source_record_count,
                planned_mapping_key: result.artifact.planned_mapping_key,
                one_to_one_mapping_expected: result.artifact.one_to_one_mapping_expected,
                duplicate_source_record_key_count: result.artifact.duplicate_source_record_key_count,
                duplicate_fragment_external_id_count: result.artifact.duplicate_fragment_external_id_count,
                missing_source_page_url_count: result.artifact.missing_source_page_url_count,
                missing_source_page_url_base_count: result.artifact.missing_source_page_url_base_count,
                missing_source_url_fragment_external_id_count:
                    result.artifact.missing_source_url_fragment_external_id_count,
                missing_source_inventory_record_key_count: result.artifact.missing_source_inventory_record_key_count,
                planned_enriched_field_count: result.artifact.planned_enriched_field_count,
                regeneration_execution_authorization_required:
                    result.artifact.regeneration_execution_authorization_required,
                no_write_verification_required: result.artifact.no_write_verification_required,
                accepted_mapping_count: result.artifact.accepted_mapping_count,
                raw_write_ready_for_execution: result.artifact.raw_write_ready_for_execution,
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
    L2V3Y_ARTIFACT_PATH,
    L2V3X_ARTIFACT_PATH,
    L2V3W_ARTIFACT_PATH,
    L2V3V_ARTIFACT_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_PATH,
    PLANNED_ENRICHED_FIELDS,
    EXECUTION_STEP,
    CONTINUE_PLANNING_STEP,
    HELPER_IMPLEMENTATION_STEP,
    parseArgs,
    validateCliOptions,
    analyzeInputPaths,
    buildHelperCoverage,
    analyzeMapping,
    validateInputs,
    buildArtifact,
    updateManifestMetadata,
    buildReport,
    runEnrichedTargetRegenerationPlan,
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
