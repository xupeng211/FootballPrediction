#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3AA';
const PHASE_NAME = 'controlled_enriched_target_regeneration_execution';
const ARTIFACT_STATUS = 'completed_controlled_no_write_enriched_target_regeneration_execution';
const GENERATED_AT = '2026-05-22T00:00:00Z';
const MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const L2V3Y_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.controlled_source_inventory_acquisition_result.phase521l2v3y.json';
const L2V3Z_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_target_regeneration_plan.phase521l2v3z.json';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_targets.phase521l2v3aa.json';
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AA.md';
const CANDIDATE_SCOPE_COUNT = 50;
const RECOMMENDED_NEXT_STEP = 'Phase 5.21L2V3AB: enriched no-write verification planning';
const NEXT_REQUIRED_STEP = 'enriched_no_write_verification_planning';
const ENRICHED_TARGET_FIELDS = Object.freeze([
    'target_id',
    'match_id',
    'external_id',
    'schedule_external_id',
    'source_page_url',
    'source_page_url_base',
    'source_url_fragment_external_id',
    'source_slug',
    'source_route_code',
    'source_url_path_slug',
    'detail_external_id_candidate',
    'detail_identity_source',
    'schedule_date',
    'schedule_home_team',
    'schedule_away_team',
    'source_inventory_record_key',
    'source_inventory_generated_at',
    'identity_evidence_status',
    'enrichment_source_artifact',
    'regeneration_status',
    'regeneration_blockers',
    'raw_write_ready_for_execution',
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

function countWhere(items, predicate) {
    return items.filter(predicate).length;
}

function loadDependencies(dependencies = {}) {
    return {
        manifest: dependencies.manifest || readJsonFile(MANIFEST_PATH),
        l2v3yArtifact: dependencies.l2v3yArtifact || readJsonFile(L2V3Y_ARTIFACT_PATH),
        l2v3zArtifact: dependencies.l2v3zArtifact || readJsonFile(L2V3Z_ARTIFACT_PATH),
    };
}

function validateInputs(manifest = {}, l2v3yArtifact = {}, l2v3zArtifact = {}) {
    const errors = [];
    const alreadyCompleted =
        normalizeText(manifest.phase_5_21_l2v3aa_execution_status) === ARTIFACT_STATUS &&
        normalizeText(manifest.enriched_target_regeneration_execution_status) === ARTIFACT_STATUS;

    if (
        normalizeText(manifest.next_required_step) !== 'controlled_enriched_target_regeneration_execution' &&
        !alreadyCompleted
    ) {
        errors.push('manifest next_required_step must be controlled_enriched_target_regeneration_execution');
    }
    if (!Array.isArray(manifest.candidate_targets) || manifest.candidate_targets.length !== CANDIDATE_SCOPE_COUNT) {
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
    if (Number(l2v3yArtifact.candidate_scope_count || 0) !== CANDIDATE_SCOPE_COUNT) {
        errors.push('L2V3Y candidate_scope_count must be 50');
    }
    if (Number(l2v3yArtifact.candidate_targets_matched_count || 0) !== CANDIDATE_SCOPE_COUNT) {
        errors.push('L2V3Y candidate_targets_matched_count must be 50');
    }
    if (Number(l2v3yArtifact.identity_evidence_complete_count || 0) !== CANDIDATE_SCOPE_COUNT) {
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
        l2v3yArtifact.source_inventory_metadata_records.length !== CANDIDATE_SCOPE_COUNT
    ) {
        errors.push('L2V3Y source_inventory_metadata_records must contain 50 records');
    }

    if (normalizeText(l2v3zArtifact.proposal_phase) !== 'Phase 5.21L2V3Z') {
        errors.push('L2V3Z artifact must be present');
    }
    if (normalizeText(l2v3zArtifact.planned_mapping_key) !== 'target_id') {
        errors.push('L2V3Z planned_mapping_key must be target_id');
    }
    if (l2v3zArtifact.one_to_one_mapping_expected !== true) {
        errors.push('L2V3Z one_to_one_mapping_expected must remain true');
    }
    if (Number(l2v3zArtifact.duplicate_source_record_key_count || 0) !== 0) {
        errors.push('L2V3Z duplicate_source_record_key_count must remain 0');
    }
    if (Number(l2v3zArtifact.duplicate_fragment_external_id_count || 0) !== 0) {
        errors.push('L2V3Z duplicate_fragment_external_id_count must remain 0');
    }
    if (Number(l2v3zArtifact.missing_source_page_url_count || 0) !== 0) {
        errors.push('L2V3Z missing_source_page_url_count must remain 0');
    }
    if (Number(l2v3zArtifact.missing_source_page_url_base_count || 0) !== 0) {
        errors.push('L2V3Z missing_source_page_url_base_count must remain 0');
    }
    if (Number(l2v3zArtifact.missing_source_url_fragment_external_id_count || 0) !== 0) {
        errors.push('L2V3Z missing_source_url_fragment_external_id_count must remain 0');
    }
    if (Number(l2v3zArtifact.missing_source_inventory_record_key_count || 0) !== 0) {
        errors.push('L2V3Z missing_source_inventory_record_key_count must remain 0');
    }
    if (Number(l2v3zArtifact.accepted_mapping_count || 0) !== 0) {
        errors.push('L2V3Z accepted_mapping_count must remain 0');
    }
    if (l2v3zArtifact.raw_write_ready_for_execution !== false) {
        errors.push('L2V3Z raw_write_ready_for_execution must remain false');
    }
    if (l2v3zArtifact.regeneration_execution_authorization_required !== true) {
        errors.push('L2V3Z regeneration_execution_authorization_required must remain true');
    }
    if (l2v3zArtifact.no_write_verification_required !== true) {
        errors.push('L2V3Z no_write_verification_required must remain true');
    }

    return { ok: errors.length === 0, errors };
}

function buildMaps(manifest = {}, l2v3yArtifact = {}) {
    const candidates = Array.isArray(manifest.candidate_targets) ? manifest.candidate_targets : [];
    const records = Array.isArray(l2v3yArtifact.source_inventory_metadata_records)
        ? l2v3yArtifact.source_inventory_metadata_records
        : [];

    return {
        candidates,
        records,
        recordsByTargetId: new Map(records.map(record => [normalizeText(record.target_id), record])),
    };
}

function compareScheduleMetadata(candidate = {}, record = {}) {
    const mismatches = [];
    if (normalizeText(candidate.match_id) !== normalizeText(record.match_id)) mismatches.push('match_id_mismatch');
    if (normalizeText(candidate.external_id) !== normalizeText(record.schedule_external_id)) {
        mismatches.push('schedule_external_id_mismatch');
    }
    if (normalizeText(record.source_url_fragment_external_id) !== normalizeText(record.schedule_external_id)) {
        mismatches.push('fragment_schedule_external_id_mismatch');
    }
    if (normalizeText(candidate.kickoff_time || candidate.match_date) !== normalizeText(record.schedule_date)) {
        mismatches.push('schedule_date_mismatch');
    }
    if (normalizeText(candidate.home_team) !== normalizeText(record.schedule_home_team)) {
        mismatches.push('schedule_home_team_mismatch');
    }
    if (normalizeText(candidate.away_team) !== normalizeText(record.schedule_away_team)) {
        mismatches.push('schedule_away_team_mismatch');
    }
    return mismatches;
}

function buildDetailIdentityFields(record = {}) {
    const detailExternalIdCandidate = /^\d+$/.test(normalizeText(record.source_url_fragment_external_id))
        ? normalizeText(record.source_url_fragment_external_id)
        : null;
    return {
        detail_external_id_candidate: detailExternalIdCandidate,
        detail_identity_source: detailExternalIdCandidate ? 'url_hash_fragment' : null,
    };
}

function buildEnrichedTarget(candidate = {}, record = {}, regenerationBlockers = []) {
    const detailIdentity = buildDetailIdentityFields(record);
    return {
        target_id: candidate.target_id,
        match_id: candidate.match_id,
        external_id: candidate.external_id,
        schedule_external_id: record.schedule_external_id,
        source_page_url: record.source_page_url,
        source_page_url_base: record.source_page_url_base,
        source_url_fragment_external_id: record.source_url_fragment_external_id,
        source_slug: record.source_slug || null,
        source_route_code: record.source_route_code || null,
        source_url_path_slug: record.source_url_path_slug || record.source_route_code || null,
        detail_external_id_candidate: detailIdentity.detail_external_id_candidate,
        detail_identity_source: detailIdentity.detail_identity_source,
        schedule_date: record.schedule_date,
        schedule_home_team: record.schedule_home_team,
        schedule_away_team: record.schedule_away_team,
        source_inventory_record_key: record.source_inventory_record_key,
        source_inventory_generated_at: record.source_inventory_generated_at,
        identity_evidence_status: record.identity_evidence_status,
        enrichment_source_artifact: L2V3Y_ARTIFACT_PATH,
        regeneration_status: regenerationBlockers.length === 0 ? 'regenerated_no_write' : 'blocked_no_write',
        regeneration_blockers: regenerationBlockers,
        raw_write_ready_for_execution: false,
    };
}

function regenerateTargets(manifest = {}, l2v3yArtifact = {}) {
    const { candidates, records, recordsByTargetId } = buildMaps(manifest, l2v3yArtifact);
    const duplicateSourceRecordKeyCount = countDuplicates(records.map(record => record.source_inventory_record_key));
    const duplicateFragmentExternalIdCount = countDuplicates(
        records.map(record => record.source_url_fragment_external_id)
    );
    const missingSourcePageUrlCount = countWhere(records, record => !normalizeText(record.source_page_url));
    const missingSourcePageUrlBaseCount = countWhere(records, record => !normalizeText(record.source_page_url_base));
    const missingSourceUrlFragmentExternalIdCount = countWhere(
        records,
        record => !normalizeText(record.source_url_fragment_external_id)
    );
    const missingSourceInventoryRecordKeyCount = countWhere(
        records,
        record => !normalizeText(record.source_inventory_record_key)
    );

    const enrichedTargets = [];
    let blockedTargetCount = 0;
    let oneToOneMappingCount = 0;
    let fragmentScheduleIdMismatchCount = 0;
    let scheduleMetadataMismatchCount = 0;

    for (const candidate of candidates) {
        const blockers = [];
        const targetId = normalizeText(candidate.target_id);
        const record = recordsByTargetId.get(targetId);
        if (!record) {
            blockers.push('missing_source_record_for_target_id');
            enrichedTargets.push(buildEnrichedTarget(candidate, {}, blockers));
            blockedTargetCount += 1;
            continue;
        }

        oneToOneMappingCount += 1;
        if (!normalizeText(record.source_page_url)) blockers.push('missing_source_page_url');
        if (!normalizeText(record.source_page_url_base)) blockers.push('missing_source_page_url_base');
        if (!normalizeText(record.source_url_fragment_external_id)) {
            blockers.push('missing_source_url_fragment_external_id');
        }
        if (!normalizeText(record.source_inventory_record_key)) blockers.push('missing_source_inventory_record_key');

        const scheduleMismatches = compareScheduleMetadata(candidate, record);
        if (scheduleMismatches.includes('fragment_schedule_external_id_mismatch')) {
            fragmentScheduleIdMismatchCount += 1;
        }
        if (scheduleMismatches.some(item => item !== 'fragment_schedule_external_id_mismatch')) {
            scheduleMetadataMismatchCount += 1;
        }
        blockers.push(...scheduleMismatches);

        if (duplicateSourceRecordKeyCount > 0 && normalizeText(record.source_inventory_record_key)) {
            blockers.push('duplicate_source_inventory_record_key_detected');
        }
        if (duplicateFragmentExternalIdCount > 0 && normalizeText(record.source_url_fragment_external_id)) {
            blockers.push('duplicate_source_url_fragment_external_id_detected');
        }

        const uniqueBlockers = [...new Set(blockers)];
        if (uniqueBlockers.length > 0) blockedTargetCount += 1;
        enrichedTargets.push(buildEnrichedTarget(candidate, record, uniqueBlockers));
    }

    return {
        enrichedTargets,
        summary: {
            candidate_scope_count: candidates.length,
            acquired_source_record_count: records.length,
            regenerated_target_count: countWhere(
                enrichedTargets,
                target => target.regeneration_status === 'regenerated_no_write'
            ),
            blocked_target_count: blockedTargetCount,
            one_to_one_mapping_count: oneToOneMappingCount,
            duplicate_source_record_key_count: duplicateSourceRecordKeyCount,
            duplicate_fragment_external_id_count: duplicateFragmentExternalIdCount,
            missing_source_page_url_count: missingSourcePageUrlCount,
            missing_source_page_url_base_count: missingSourcePageUrlBaseCount,
            missing_source_url_fragment_external_id_count: missingSourceUrlFragmentExternalIdCount,
            missing_source_inventory_record_key_count: missingSourceInventoryRecordKeyCount,
            fragment_schedule_id_mismatch_count: fragmentScheduleIdMismatchCount,
            schedule_metadata_mismatch_count: scheduleMetadataMismatchCount,
            identity_evidence_complete_count: countWhere(
                enrichedTargets,
                target => normalizeText(target.identity_evidence_status) === 'complete'
            ),
            detail_identity_candidate_count: countWhere(enrichedTargets, target =>
                normalizeText(target.detail_external_id_candidate)
            ),
            raw_write_ready_target_count: 0,
            accepted_mapping_count: 0,
            raw_write_ready_for_execution: false,
            no_write_verification_required: true,
            recommended_next_step: RECOMMENDED_NEXT_STEP,
        },
    };
}

function buildArtifact({ manifest = {}, l2v3yArtifact = {}, l2v3zArtifact = {}, generatedAt = GENERATED_AT } = {}) {
    const regeneration = regenerateTargets(manifest, l2v3yArtifact);
    return {
        artifact_type: 'enriched_targets',
        artifact_status: ARTIFACT_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        source_phase: 'Phase 5.21L2V3Z',
        generated_at: generatedAt,
        regeneration_attempted: true,
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
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        baseline_replacement_accepted: false,
        raw_write_authorization_performed: false,
        raw_write_retry_performed: false,
        enriched_target_regeneration_execution_performed: true,
        candidate_scope_count: regeneration.summary.candidate_scope_count,
        acquired_source_record_count: regeneration.summary.acquired_source_record_count,
        regenerated_target_count: regeneration.summary.regenerated_target_count,
        blocked_target_count: regeneration.summary.blocked_target_count,
        one_to_one_mapping_count: regeneration.summary.one_to_one_mapping_count,
        duplicate_source_record_key_count: regeneration.summary.duplicate_source_record_key_count,
        duplicate_fragment_external_id_count: regeneration.summary.duplicate_fragment_external_id_count,
        missing_source_page_url_count: regeneration.summary.missing_source_page_url_count,
        missing_source_page_url_base_count: regeneration.summary.missing_source_page_url_base_count,
        missing_source_url_fragment_external_id_count:
            regeneration.summary.missing_source_url_fragment_external_id_count,
        missing_source_inventory_record_key_count: regeneration.summary.missing_source_inventory_record_key_count,
        fragment_schedule_id_mismatch_count: regeneration.summary.fragment_schedule_id_mismatch_count,
        schedule_metadata_mismatch_count: regeneration.summary.schedule_metadata_mismatch_count,
        identity_evidence_complete_count: regeneration.summary.identity_evidence_complete_count,
        detail_identity_candidate_count: regeneration.summary.detail_identity_candidate_count,
        raw_write_ready_target_count: 0,
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
        no_write_verification_required: true,
        planned_mapping_key: l2v3zArtifact.planned_mapping_key,
        planned_cross_check_keys: l2v3zArtifact.planned_cross_check_keys || [],
        enriched_target_field_count: ENRICHED_TARGET_FIELDS.length,
        enriched_target_fields: ENRICHED_TARGET_FIELDS,
        safety_contract: {
            enriched_target_result_is_not_accepted_mapping: true,
            enriched_target_result_is_not_raw_write_authorization: true,
            identity_evidence_complete_does_not_imply_raw_write_ready_for_execution: true,
            separate_identity_mapping_acceptance_required: true,
            separate_baseline_acceptance_required: true,
            separate_final_db_write_authorization_required: true,
            no_write_verification_remains_required: true,
        },
        enriched_targets: regeneration.enrichedTargets,
        recommended_next_step: RECOMMENDED_NEXT_STEP,
        next_required_step: NEXT_REQUIRED_STEP,
    };
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    return {
        ...manifest,
        phase_5_21_l2v3aa_execution_status: artifact.artifact_status,
        enriched_target_regeneration_execution_status: artifact.artifact_status,
        phase_5_21_l2v3aa_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3aa_report_path: REPORT_PATH,
        regeneration_attempted: true,
        live_fetch_performed: false,
        db_write_performed: false,
        candidate_scope_count: artifact.candidate_scope_count,
        phase_5_21_l2v3aa_candidate_scope_count: artifact.candidate_scope_count,
        regenerated_target_count: artifact.regenerated_target_count,
        phase_5_21_l2v3aa_regenerated_target_count: artifact.regenerated_target_count,
        blocked_target_count: artifact.blocked_target_count,
        phase_5_21_l2v3aa_blocked_target_count: artifact.blocked_target_count,
        acquired_source_record_count: artifact.acquired_source_record_count,
        phase_5_21_l2v3aa_acquired_source_record_count: artifact.acquired_source_record_count,
        one_to_one_mapping_count: artifact.one_to_one_mapping_count,
        phase_5_21_l2v3aa_one_to_one_mapping_count: artifact.one_to_one_mapping_count,
        duplicate_source_record_key_count: artifact.duplicate_source_record_key_count,
        phase_5_21_l2v3aa_duplicate_source_record_key_count: artifact.duplicate_source_record_key_count,
        duplicate_fragment_external_id_count: artifact.duplicate_fragment_external_id_count,
        phase_5_21_l2v3aa_duplicate_fragment_external_id_count: artifact.duplicate_fragment_external_id_count,
        missing_source_page_url_count: artifact.missing_source_page_url_count,
        phase_5_21_l2v3aa_missing_source_page_url_count: artifact.missing_source_page_url_count,
        missing_source_page_url_base_count: artifact.missing_source_page_url_base_count,
        phase_5_21_l2v3aa_missing_source_page_url_base_count: artifact.missing_source_page_url_base_count,
        missing_source_url_fragment_external_id_count: artifact.missing_source_url_fragment_external_id_count,
        phase_5_21_l2v3aa_missing_source_url_fragment_external_id_count:
            artifact.missing_source_url_fragment_external_id_count,
        missing_source_inventory_record_key_count: artifact.missing_source_inventory_record_key_count,
        phase_5_21_l2v3aa_missing_source_inventory_record_key_count: artifact.missing_source_inventory_record_key_count,
        fragment_schedule_id_mismatch_count: artifact.fragment_schedule_id_mismatch_count,
        phase_5_21_l2v3aa_fragment_schedule_id_mismatch_count: artifact.fragment_schedule_id_mismatch_count,
        schedule_metadata_mismatch_count: artifact.schedule_metadata_mismatch_count,
        phase_5_21_l2v3aa_schedule_metadata_mismatch_count: artifact.schedule_metadata_mismatch_count,
        identity_evidence_complete_count: artifact.identity_evidence_complete_count,
        detail_identity_candidate_count: artifact.detail_identity_candidate_count,
        phase_5_21_l2v3aa_detail_identity_candidate_count: artifact.detail_identity_candidate_count,
        phase_5_21_l2v3aa_identity_evidence_complete_count: artifact.identity_evidence_complete_count,
        raw_write_ready_target_count: 0,
        phase_5_21_l2v3aa_raw_write_ready_target_count: 0,
        accepted_mapping_count: 0,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        no_write_verification_required: true,
        phase_5_21_l2v3aa_no_write_verification_required: true,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

function buildReport(artifact = {}) {
    return `# Data Entrypoint Governance - Phase 5.21 L2V3AA

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- regeneration_attempted=true
- live_fetch_performed=false
- db_write_performed=false
- raw_match_data_insert_performed=false
- matches_write_performed=false
- matches_external_id_modified=false
- schema_migration_performed=false
- parser_features_training_prediction_performed=false
- browser_proxy_captcha_bypass_performed=false

## Classification Output

- candidate_scope_count=${artifact.candidate_scope_count}
- acquired_source_record_count=${artifact.acquired_source_record_count}
- regenerated_target_count=${artifact.regenerated_target_count}
- blocked_target_count=${artifact.blocked_target_count}
- one_to_one_mapping_count=${artifact.one_to_one_mapping_count}
- duplicate_source_record_key_count=${artifact.duplicate_source_record_key_count}
- duplicate_fragment_external_id_count=${artifact.duplicate_fragment_external_id_count}
- missing_source_page_url_count=${artifact.missing_source_page_url_count}
- missing_source_page_url_base_count=${artifact.missing_source_page_url_base_count}
- missing_source_url_fragment_external_id_count=${artifact.missing_source_url_fragment_external_id_count}
- missing_source_inventory_record_key_count=${artifact.missing_source_inventory_record_key_count}
- fragment_schedule_id_mismatch_count=${artifact.fragment_schedule_id_mismatch_count}
- schedule_metadata_mismatch_count=${artifact.schedule_metadata_mismatch_count}
- identity_evidence_complete_count=${artifact.identity_evidence_complete_count}
- detail_identity_candidate_count=${artifact.detail_identity_candidate_count}
- raw_write_ready_target_count=0
- accepted_mapping_count=0
- raw_write_ready_for_execution=false
- no_write_verification_required=true

## Mapping

- planned_mapping_key=${artifact.planned_mapping_key}
- planned_cross_check_keys=${artifact.planned_cross_check_keys.join(', ')}

## Enriched Target Fields

${artifact.enriched_target_fields.map(field => `- ${field}`).join('\n')}

## Safety Contract

- enriched target result is not accepted mapping.
- enriched target result is not raw write authorization.
- identity_evidence_complete does not imply raw_write_ready_for_execution.
- no-write verification remains required.
- separate identity mapping acceptance is required.
- separate baseline acceptance is required.
- separate final DB-write authorization is required.

## Next Step

${artifact.recommended_next_step}
`;
}

function runEnrichedTargetRegenerationExecution(dependencies = {}) {
    const loaded = loadDependencies(dependencies);
    const inputGate = validateInputs(loaded.manifest, loaded.l2v3yArtifact, loaded.l2v3zArtifact);
    if (!inputGate.ok) return { ok: false, status: 3, errors: inputGate.errors };

    const artifact = buildArtifact({
        manifest: loaded.manifest,
        l2v3yArtifact: loaded.l2v3yArtifact,
        l2v3zArtifact: loaded.l2v3zArtifact,
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
        '  node scripts/ops/pageprops_v2_enriched_target_regeneration_execute.js --write-files=yes',
        '',
        'Safety:',
        '  L2V3AA is a controlled no-write enriched target regeneration execution phase.',
        '  It does not live fetch, write DB/raw/matches, accept mappings, accept baselines, or retry raw writes.',
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
    const result = runEnrichedTargetRegenerationExecution({ writeFiles: options.writeFiles });
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
                regeneration_attempted: result.artifact.regeneration_attempted,
                live_fetch_performed: result.artifact.live_fetch_performed,
                db_write_performed: result.artifact.db_write_performed,
                candidate_scope_count: result.artifact.candidate_scope_count,
                acquired_source_record_count: result.artifact.acquired_source_record_count,
                regenerated_target_count: result.artifact.regenerated_target_count,
                blocked_target_count: result.artifact.blocked_target_count,
                one_to_one_mapping_count: result.artifact.one_to_one_mapping_count,
                duplicate_source_record_key_count: result.artifact.duplicate_source_record_key_count,
                duplicate_fragment_external_id_count: result.artifact.duplicate_fragment_external_id_count,
                missing_source_page_url_count: result.artifact.missing_source_page_url_count,
                missing_source_page_url_base_count: result.artifact.missing_source_page_url_base_count,
                missing_source_url_fragment_external_id_count:
                    result.artifact.missing_source_url_fragment_external_id_count,
                missing_source_inventory_record_key_count: result.artifact.missing_source_inventory_record_key_count,
                fragment_schedule_id_mismatch_count: result.artifact.fragment_schedule_id_mismatch_count,
                schedule_metadata_mismatch_count: result.artifact.schedule_metadata_mismatch_count,
                identity_evidence_complete_count: result.artifact.identity_evidence_complete_count,
                raw_write_ready_target_count: result.artifact.raw_write_ready_target_count,
                accepted_mapping_count: result.artifact.accepted_mapping_count,
                raw_write_ready_for_execution: result.artifact.raw_write_ready_for_execution,
                no_write_verification_required: result.artifact.no_write_verification_required,
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
    L2V3Z_ARTIFACT_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_PATH,
    ENRICHED_TARGET_FIELDS,
    parseArgs,
    validateCliOptions,
    validateInputs,
    regenerateTargets,
    buildArtifact,
    updateManifestMetadata,
    buildReport,
    runEnrichedTargetRegenerationExecution,
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
