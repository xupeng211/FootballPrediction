#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3U';
const PHASE_NAME = 'source_inventory_enrichment_planning';
const ARTIFACT_STATUS = 'completed_no_write_source_inventory_enrichment_planning';
const GENERATED_AT = '2026-05-21T08:00:00Z';
const MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const L2V3N_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.expanded_date_rule_verification.phase521l2v3n.json';
const L2V3P_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.metadata_only_detail_check.phase521l2v3p.json';
const L2V3Q_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.continued_metadata_investigation.phase521l2v3q.json';
const L2V3R_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.detail_url_construction_fix_plan.phase521l2v3r.json';
const L2V3T_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.continued_detail_endpoint_investigation.phase521l2v3t.json';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.source_inventory_enrichment_plan.phase521l2v3u.json';
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3U.md';
const NEXT_RECOMMENDED_STEP = 'Phase 5.21L2V3V: source inventory enrichment implementation';
const NEXT_REQUIRED_STEP = 'source_inventory_enrichment_implementation';
const ENRICHMENT_STRATEGY = 'source_controlled_manifest_candidate_enrichment_from_source_inventory_pageUrl_metadata';

const INPUT_PATHS = Object.freeze([
    { key: 'manifest', path: MANIFEST_PATH, role: 'current_manifest' },
    { key: 'l2v3t_artifact', path: L2V3T_ARTIFACT_PATH, role: 'continued_detail_endpoint_investigation' },
    { key: 'l2v3t_report', path: 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3T.md', role: 'report' },
    { key: 'l2v3r_artifact', path: L2V3R_ARTIFACT_PATH, role: 'detail_url_construction_plan' },
    { key: 'l2v3r_report', path: 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3R.md', role: 'report' },
    { key: 'l2v3q_artifact', path: L2V3Q_ARTIFACT_PATH, role: 'continued_metadata_investigation' },
    { key: 'l2v3q_report', path: 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3Q.md', role: 'report' },
    { key: 'l2v3p_artifact', path: L2V3P_ARTIFACT_PATH, role: 'metadata_only_detail_check' },
    { key: 'l2v3p_report', path: 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3P.md', role: 'report' },
    { key: 'l2v3n_artifact', path: L2V3N_ARTIFACT_PATH, role: 'expanded_date_rule_verification' },
    { key: 'l2v3n_report', path: 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3N.md', role: 'report' },
    {
        key: 'source_inventory_preflight',
        path: 'scripts/ops/single_league_target_discovery_source_inventory_preflight.js',
        role: 'source_inventory_generation_script',
    },
    {
        key: 'source_inventory_adapter',
        path: 'src/infrastructure/services/FotMobSourceInventoryAdapter.js',
        role: 'source_inventory_adapter',
    },
    {
        key: 'source_inventory_reconciliation',
        path: 'scripts/ops/pageprops_v2_target_source_inventory_reconciliation_plan.js',
        role: 'source_inventory_reconciliation_script',
    },
    {
        key: 'no_write_preview',
        path: 'scripts/ops/pageprops_v2_no_write_preview.js',
        role: 'no_write_preview_helper',
    },
    {
        key: 'metadata_only_helper',
        path: 'scripts/ops/pageprops_v2_metadata_only_detail_check.js',
        role: 'metadata_only_helper',
    },
    {
        key: 'candidate_manifest_generation',
        path: 'scripts/ops/single_league_small_batch_target_manifest_plan.js',
        role: 'candidate_target_generation_code',
    },
    {
        key: 'source_inventory_preflight_test',
        path: 'tests/unit/single_league_target_discovery_source_inventory_preflight.test.js',
        role: 'source_inventory_test',
    },
    {
        key: 'source_inventory_reconciliation_test',
        path: 'tests/unit/pageprops_v2_target_source_inventory_reconciliation_plan.test.js',
        role: 'source_inventory_test',
    },
]);

const PROPOSED_ENRICHMENT_FIELDS = Object.freeze([
    {
        field: 'source_page_url',
        aliases: ['source_page_url', 'page_url', 'pageUrl'],
        persistence_layer: 'manifest_candidate_target',
        purpose: 'requested-side FotMob page URL captured from source inventory',
    },
    {
        field: 'source_page_url_base',
        aliases: ['source_page_url_base', 'page_url_base', 'source_inventory_page_url_base', 'manifest_page_url_base'],
        persistence_layer: 'manifest_candidate_target',
        purpose: 'requested-side page URL without fragment for slug reuse detection',
    },
    {
        field: 'source_url_fragment_external_id',
        aliases: ['source_url_fragment_external_id', 'source_page_url_fragment_external_id', 'page_url_anchor'],
        persistence_layer: 'manifest_candidate_target',
        purpose: 'external id encoded after the URL fragment',
    },
    {
        field: 'source_slug',
        aliases: ['source_slug', 'page_url_slug', 'detail_route_slug'],
        persistence_layer: 'manifest_candidate_target',
        purpose: 'slug segment from the requested source inventory URL',
    },
    {
        field: 'source_route_code',
        aliases: ['source_route_code', 'page_url_route_code', 'detail_route_code'],
        persistence_layer: 'manifest_candidate_target',
        purpose: 'stable route code segment from the requested source inventory URL',
    },
    {
        field: 'schedule_external_id',
        aliases: ['schedule_external_id', 'external_id'],
        persistence_layer: 'manifest_candidate_target',
        purpose: 'requested schedule id; equivalent currently exists as external_id',
    },
    {
        field: 'schedule_date',
        aliases: ['schedule_date', 'match_date', 'kickoff_time'],
        persistence_layer: 'manifest_candidate_target',
        purpose: 'requested schedule date used for requested-vs-observed checks',
    },
    {
        field: 'schedule_home_team',
        aliases: ['schedule_home_team', 'home_team'],
        persistence_layer: 'manifest_candidate_target',
        purpose: 'requested home team from source inventory',
    },
    {
        field: 'schedule_away_team',
        aliases: ['schedule_away_team', 'away_team'],
        persistence_layer: 'manifest_candidate_target',
        purpose: 'requested away team from source inventory',
    },
    {
        field: 'source_inventory_record_key',
        aliases: ['source_inventory_record_key'],
        persistence_layer: 'manifest_candidate_target',
        purpose: 'deterministic source inventory path plus external id key',
    },
    {
        field: 'source_inventory_generated_at',
        aliases: ['source_inventory_generated_at'],
        persistence_layer: 'manifest_metadata',
        purpose: 'timestamp of the authorized source inventory regeneration run',
    },
    {
        field: 'identity_evidence_status',
        aliases: ['identity_evidence_status'],
        persistence_layer: 'manifest_candidate_target',
        purpose: 'explicit blocker/pass status for source URL identity evidence',
    },
]);

function absolutePath(filePath) {
    if (path.isAbsolute(filePath)) return filePath;
    return path.join(PROJECT_ROOT, filePath);
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

function normalizeLower(value) {
    return normalizeText(value).toLowerCase();
}

function normalizeBooleanFlag(value, fallback = false) {
    if (typeof value === 'boolean') return value;
    if (value === null || value === undefined || value === '') return fallback;
    const text = normalizeLower(value);
    if (['1', 'true', 'yes', 'y', 'on'].includes(text)) return true;
    if (['0', 'false', 'no', 'n', 'off'].includes(text)) return false;
    return fallback;
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
        help: 'help',
        h: 'help',
    };

    for (let index = 0; index < argv.length; index += 1) {
        const arg = String(argv[index]);
        if (!arg.startsWith('--')) {
            options.unknown.push(arg);
            continue;
        }
        const key = arg.replace(/^--/, '').split('=')[0];
        const mapped = keyMap[key];
        if (!mapped) {
            options.unknown.push(key);
            continue;
        }
        const value = arg.includes('=')
            ? arg.slice(arg.indexOf('=') + 1)
            : argv[index + 1] && !String(argv[index + 1]).startsWith('--')
              ? argv[++index]
              : true;
        options[mapped] = normalizeBooleanFlag(value, true);
    }
    return options;
}

function validateCliOptions(options = {}) {
    const errors = [];
    if (Array.isArray(options.unknown) && options.unknown.length > 0) {
        errors.push(`unknown arguments: ${options.unknown.join(', ')}`);
    }
    return { ok: errors.length === 0, errors };
}

function fieldHasValue(target = {}, definition = {}) {
    return definition.aliases.some(alias => normalizeText(target[alias]));
}

function countMissing(targets = [], definition = {}) {
    return targets.filter(target => !fieldHasValue(target, definition)).length;
}

function buildFieldGapSummary(manifest = {}) {
    const targets = Array.isArray(manifest.candidate_targets) ? manifest.candidate_targets : [];
    const byField = Object.fromEntries(
        PROPOSED_ENRICHMENT_FIELDS.map(definition => [
            definition.field,
            {
                missing_count: countMissing(targets, definition),
                present_or_equivalent_count: targets.length - countMissing(targets, definition),
                aliases_checked: definition.aliases,
                persistence_layer: definition.persistence_layer,
            },
        ])
    );
    const manifestCandidateFieldGapCount = Object.values(byField).reduce(
        (total, entry) => total + entry.missing_count,
        0
    );
    return {
        candidate_targets_count: targets.length,
        proposed_new_field_count: PROPOSED_ENRICHMENT_FIELDS.length,
        manifest_candidate_field_gap_count: manifestCandidateFieldGapCount,
        missing_source_page_url_count: byField.source_page_url?.missing_count || 0,
        missing_page_url_base_count: byField.source_page_url_base?.missing_count || 0,
        missing_url_fragment_external_id_count: byField.source_url_fragment_external_id?.missing_count || 0,
        missing_source_record_key_count: byField.source_inventory_record_key?.missing_count || 0,
        missing_source_slug_count: byField.source_slug?.missing_count || 0,
        missing_source_route_code_count: byField.source_route_code?.missing_count || 0,
        source_identity_evidence_field_gap_count:
            (byField.source_page_url?.missing_count || 0) +
            (byField.source_page_url_base?.missing_count || 0) +
            (byField.source_url_fragment_external_id?.missing_count || 0) +
            (byField.source_inventory_record_key?.missing_count || 0),
        by_field: byField,
    };
}

function analyzeInputPaths(inputPaths = INPUT_PATHS, dependencies = {}) {
    return inputPaths.map(item => {
        const exists =
            dependencies.existingPaths instanceof Set
                ? dependencies.existingPaths.has(item.path)
                : fs.existsSync(absolutePath(item.path));
        let matchedPatternCount = 0;
        if (exists && dependencies.skipPathTextRead !== true) {
            const text =
                dependencies.sourceTextByPath &&
                Object.prototype.hasOwnProperty.call(dependencies.sourceTextByPath, item.path)
                    ? dependencies.sourceTextByPath[item.path]
                    : readTextFile(item.path);
            matchedPatternCount = ['source_inventory', 'pageUrl', 'page_url_base', 'candidate_targets'].filter(
                pattern => text.includes(pattern)
            ).length;
        }
        return {
            key: item.key,
            path: item.path,
            role: item.role,
            exists,
            matched_pattern_count: matchedPatternCount,
            source_inventory_related:
                item.key.includes('source_inventory') ||
                item.role.includes('source_inventory') ||
                item.path.includes('source_inventory'),
        };
    });
}

function validateInputs(manifest = {}, l2v3tArtifact = {}) {
    const errors = [];
    const nextRequiredStep = normalizeText(manifest.next_required_step);
    const alreadyCompleted =
        nextRequiredStep === NEXT_REQUIRED_STEP &&
        normalizeText(manifest.phase_5_21_l2v3u_planning_status) === ARTIFACT_STATUS;
    if (nextRequiredStep !== 'source_inventory_enrichment_planning' && !alreadyCompleted) {
        errors.push('manifest next_required_step must be source_inventory_enrichment_planning');
    }
    if (manifest.raw_write_ready_for_execution !== false) {
        errors.push('manifest raw_write_ready_for_execution must remain false');
    }
    if (Number(manifest.accepted_mapping_count || 0) !== 0) {
        errors.push('manifest accepted_mapping_count must remain 0');
    }
    if (normalizeText(l2v3tArtifact.proposal_phase) !== 'Phase 5.21L2V3T') {
        errors.push('L2V3T artifact must be present');
    }
    if (l2v3tArtifact.controlled_live_check_performed !== false) {
        errors.push('L2V3T controlled_live_check_performed must be false');
    }
    if (l2v3tArtifact.network_request_performed !== false) {
        errors.push('L2V3T network_request_performed must be false');
    }
    if (normalizeText(l2v3tArtifact.previous_endpoint_status) !== 'blocked_http_403') {
        errors.push('L2V3T previous_endpoint_status must remain blocked_http_403');
    }
    if (normalizeText(l2v3tArtifact.precise_detail_endpoint_found) !== 'unknown') {
        errors.push('L2V3T precise_detail_endpoint_found must remain unknown');
    }
    if (normalizeText(l2v3tArtifact.endpoint_avoids_slug_reuse) !== 'unknown') {
        errors.push('L2V3T endpoint_avoids_slug_reuse must remain unknown');
    }
    if (Number(l2v3tArtifact.accepted_mapping_count || 0) !== 0) {
        errors.push('L2V3T accepted_mapping_count must remain 0');
    }
    if (l2v3tArtifact.raw_write_ready_for_execution !== false) {
        errors.push('L2V3T raw_write_ready_for_execution must remain false');
    }
    return { ok: errors.length === 0, errors };
}

function buildPersistencePlan() {
    return [
        {
            layer: 'source_inventory',
            status: 'future_authorized_regeneration_required',
            fields: 'pageUrl/page_url_base/url_fragment_external_id/source_slug/source_route_code/source_inventory_record_key',
            db_write_allowed: false,
        },
        {
            layer: 'manifest_candidate_target',
            status: 'planned_target_enrichment_layer',
            fields: PROPOSED_ENRICHMENT_FIELDS.map(item => item.field),
            db_write_allowed: false,
        },
        {
            layer: 'no_write_metadata_artifact',
            status: 'records_gap_counts_and_blockers_only',
            fields: 'gap counts, proposed schema, blocker status',
            db_write_allowed: false,
        },
        {
            layer: 'db_matches_metadata',
            status: 'not_recommended_for_this_phase',
            fields: 'none',
            db_write_allowed: false,
        },
    ];
}

function buildUsagePlan() {
    return [
        'detect whether requested-side pageUrl base is reused by a different observed detail fixture',
        'compare requested schedule external id with source URL fragment external id before any mapping review',
        'separate reverse fixture, slug reuse, and unresolved large-gap cases without relying on observed pageUrl only',
        'block raw write when requested-side source URL evidence is missing or inconsistent',
        'feed a future source inventory enrichment implementation or route target regeneration plan',
    ];
}

function buildArtifact({
    manifest = {},
    l2v3tArtifact = {},
    l2v3rArtifact = {},
    l2v3qArtifact = {},
    l2v3pArtifact = {},
    l2v3nArtifact = {},
    inputPathAnalysis = [],
    generatedAt = GENERATED_AT,
} = {}) {
    const fieldGapSummary = buildFieldGapSummary(manifest);
    const analyzedInventoryPathCount = inputPathAnalysis.filter(item => item.exists === true).length;
    const sourceInventoryFileCount = inputPathAnalysis.filter(
        item => item.exists === true && item.source_inventory_related === true
    ).length;
    const requiresFollowupImplementation =
        fieldGapSummary.missing_source_page_url_count > 0 ||
        fieldGapSummary.missing_page_url_base_count > 0 ||
        fieldGapSummary.missing_url_fragment_external_id_count > 0 ||
        fieldGapSummary.missing_source_record_key_count > 0;
    const requiresTargetRegeneration = requiresFollowupImplementation;
    const enrichmentConfidence =
        l2v3tArtifact.evidence_summary?.source_inventory_page_url_extraction_supported === true ? 'medium' : 'low';

    return {
        artifact_type: 'source_inventory_enrichment_plan',
        artifact_status: ARTIFACT_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        source_phase: 'Phase 5.21L2V3T',
        generated_at: generatedAt,
        no_write: true,
        live_source_check_performed: false,
        controlled_live_check_performed: false,
        network_request_performed: false,
        db_write_performed: false,
        raw_insert_performed: false,
        matches_write_performed: false,
        matches_external_id_modified: false,
        schema_migration_performed: false,
        parser_features_training_prediction_performed: false,
        browser_proxy_captcha_bypass_performed: false,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        accepted_mapping_count: 0,
        baseline_replacement_accepted: false,
        raw_write_authorization_performed: false,
        previous_endpoint_status: l2v3tArtifact.previous_endpoint_status || 'blocked_http_403',
        precise_detail_endpoint_found: l2v3tArtifact.precise_detail_endpoint_found || 'unknown',
        endpoint_avoids_slug_reuse: l2v3tArtifact.endpoint_avoids_slug_reuse || 'unknown',
        analyzed_inventory_path_count: analyzedInventoryPathCount,
        source_inventory_file_count: sourceInventoryFileCount,
        manifest_candidate_field_gap_count: fieldGapSummary.manifest_candidate_field_gap_count,
        missing_source_page_url_count: fieldGapSummary.missing_source_page_url_count,
        missing_page_url_base_count: fieldGapSummary.missing_page_url_base_count,
        missing_url_fragment_external_id_count: fieldGapSummary.missing_url_fragment_external_id_count,
        missing_source_record_key_count: fieldGapSummary.missing_source_record_key_count,
        proposed_new_field_count: fieldGapSummary.proposed_new_field_count,
        enrichment_strategy: ENRICHMENT_STRATEGY,
        enrichment_confidence: enrichmentConfidence,
        requires_followup_implementation: requiresFollowupImplementation,
        requires_target_regeneration: requiresTargetRegeneration,
        identity_evidence_status: requiresFollowupImplementation
            ? 'blocked_pending_source_inventory_enrichment'
            : 'source_inventory_evidence_present_for_review',
        current_manifest_gap_summary: fieldGapSummary,
        proposed_enrichment_fields: PROPOSED_ENRICHMENT_FIELDS.map(item => ({
            field: item.field,
            aliases: item.aliases,
            persistence_layer: item.persistence_layer,
            purpose: item.purpose,
        })),
        persistence_plan: buildPersistencePlan(),
        future_usage_plan: buildUsagePlan(),
        analyzed_inputs: inputPathAnalysis,
        upstream_context: {
            l2v3t_endpoint_investigation_result: l2v3tArtifact.endpoint_investigation_result || null,
            l2v3t_recommended_strategy: l2v3tArtifact.recommended_strategy || null,
            l2v3r_current_url_strategy: l2v3rArtifact.current_url_strategy || null,
            l2v3r_uses_source_inventory_page_url: l2v3rArtifact.uses_source_inventory_page_url ?? null,
            l2v3q_missing_pageurl_base_count: l2v3qArtifact.missing_pageurl_base_count ?? null,
            l2v3q_detail_url_construction_suspect_count: l2v3qArtifact.detail_url_construction_suspect_count ?? null,
            l2v3p_checked_target_count: l2v3pArtifact.checked_target_count ?? null,
            l2v3n_checked_target_count: l2v3nArtifact.checked_target_count ?? null,
        },
        safety_contract: {
            source_inventory_enrichment_plan_is_not_accepted_mapping: true,
            source_inventory_enrichment_plan_is_not_raw_write_authorization: true,
            source_inventory_enrichment_plan_is_not_baseline_acceptance: true,
            source_inventory_enrichment_plan_is_not_raw_write_retry: true,
            enrichment_does_not_unblock_raw_write: true,
            missing_page_url_base_remains_blocker: fieldGapSummary.missing_page_url_base_count > 0,
            separate_identity_mapping_acceptance_required: true,
            separate_baseline_acceptance_required: true,
            separate_final_db_write_authorization_required: true,
        },
        recommended_next_step: NEXT_RECOMMENDED_STEP,
        next_required_step: NEXT_REQUIRED_STEP,
    };
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    return {
        ...manifest,
        phase_5_21_l2v3u_planning_status: artifact.artifact_status,
        source_inventory_enrichment_planning_status: artifact.artifact_status,
        phase_5_21_l2v3u_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3u_report_path: REPORT_PATH,
        analyzed_inventory_path_count: artifact.analyzed_inventory_path_count,
        phase_5_21_l2v3u_analyzed_inventory_path_count: artifact.analyzed_inventory_path_count,
        source_inventory_file_count: artifact.source_inventory_file_count,
        phase_5_21_l2v3u_source_inventory_file_count: artifact.source_inventory_file_count,
        manifest_candidate_field_gap_count: artifact.manifest_candidate_field_gap_count,
        phase_5_21_l2v3u_manifest_candidate_field_gap_count: artifact.manifest_candidate_field_gap_count,
        missing_source_page_url_count: artifact.missing_source_page_url_count,
        phase_5_21_l2v3u_missing_source_page_url_count: artifact.missing_source_page_url_count,
        missing_page_url_base_count: artifact.missing_page_url_base_count,
        phase_5_21_l2v3u_missing_page_url_base_count: artifact.missing_page_url_base_count,
        missing_url_fragment_external_id_count: artifact.missing_url_fragment_external_id_count,
        phase_5_21_l2v3u_missing_url_fragment_external_id_count: artifact.missing_url_fragment_external_id_count,
        missing_source_record_key_count: artifact.missing_source_record_key_count,
        phase_5_21_l2v3u_missing_source_record_key_count: artifact.missing_source_record_key_count,
        proposed_new_field_count: artifact.proposed_new_field_count,
        phase_5_21_l2v3u_proposed_new_field_count: artifact.proposed_new_field_count,
        enrichment_strategy: artifact.enrichment_strategy,
        phase_5_21_l2v3u_enrichment_strategy: artifact.enrichment_strategy,
        enrichment_confidence: artifact.enrichment_confidence,
        phase_5_21_l2v3u_enrichment_confidence: artifact.enrichment_confidence,
        requires_followup_implementation: artifact.requires_followup_implementation,
        phase_5_21_l2v3u_requires_followup_implementation: artifact.requires_followup_implementation,
        requires_target_regeneration: artifact.requires_target_regeneration,
        phase_5_21_l2v3u_requires_target_regeneration: artifact.requires_target_regeneration,
        accepted_mapping_count: 0,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        phase_5_21_l2v3u_accepted_mapping_count: 0,
        phase_5_21_l2v3u_identity_mapping_acceptance_performed: false,
        phase_5_21_l2v3u_baseline_acceptance_performed: false,
        phase_5_21_l2v3u_raw_write_retry_performed: false,
        phase_5_21_l2v3u_raw_write_ready_for_execution: false,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

function buildReport(artifact = {}) {
    return `# Data Entrypoint Governance - Phase 5.21 L2V3U

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- no_write=true
- network_request_performed=false
- db_write_performed=false
- raw_insert_performed=false
- matches_write_performed=false
- matches_external_id_modified=false
- schema_migration_performed=false
- parser_features_training_prediction_performed=false
- browser_proxy_captcha_bypass_performed=false

## Classification Output

- analyzed_inventory_path_count=${artifact.analyzed_inventory_path_count}
- source_inventory_file_count=${artifact.source_inventory_file_count}
- manifest_candidate_field_gap_count=${artifact.manifest_candidate_field_gap_count}
- missing_source_page_url_count=${artifact.missing_source_page_url_count}
- missing_page_url_base_count=${artifact.missing_page_url_base_count}
- missing_url_fragment_external_id_count=${artifact.missing_url_fragment_external_id_count}
- missing_source_record_key_count=${artifact.missing_source_record_key_count}
- proposed_new_field_count=${artifact.proposed_new_field_count}
- enrichment_strategy=${artifact.enrichment_strategy}
- enrichment_confidence=${artifact.enrichment_confidence}
- requires_followup_implementation=${artifact.requires_followup_implementation}
- requires_target_regeneration=${artifact.requires_target_regeneration}
- accepted_mapping_count=0
- raw_write_ready_for_execution=false

## Current Gaps

- Current candidate targets do not persist requested-side source_page_url.
- Current candidate targets do not persist requested-side source_page_url_base.
- Current candidate targets do not persist source_url_fragment_external_id.
- Current candidate targets do not persist source_inventory_record_key.
- Existing schedule identity fields can be used as equivalents for schedule_external_id, schedule_date, schedule_home_team, and schedule_away_team, but the requested-side URL identity evidence remains missing.

## Proposed Enrichment Fields

${artifact.proposed_enrichment_fields.map(item => `- ${item.field}: ${item.purpose}`).join('\n')}

## Strategy

Future implementation should enrich or regenerate the source-controlled manifest from an authorized source inventory route and persist requested-side pageUrl evidence into each candidate target. This phase does not perform that implementation and does not make the enriched evidence accepted.

The enriched fields should be used to detect pageUrl base reuse, distinguish reverse fixture / slug reuse / unresolved large-gap cases, and block raw write when requested-side URL evidence is missing or inconsistent.

## Safety Contract

- source inventory enrichment plan is not accepted mapping.
- source inventory enrichment plan is not raw write authorization.
- source inventory enrichment plan is not baseline acceptance.
- source inventory enrichment plan is not raw write retry.
- enrichment does not unblock raw write.
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
        l2v3nArtifact: dependencies.l2v3nArtifact || readJsonFile(L2V3N_ARTIFACT_PATH),
        l2v3pArtifact: dependencies.l2v3pArtifact || readJsonFile(L2V3P_ARTIFACT_PATH),
        l2v3qArtifact: dependencies.l2v3qArtifact || readJsonFile(L2V3Q_ARTIFACT_PATH),
        l2v3rArtifact: dependencies.l2v3rArtifact || readJsonFile(L2V3R_ARTIFACT_PATH),
        l2v3tArtifact: dependencies.l2v3tArtifact || readJsonFile(L2V3T_ARTIFACT_PATH),
    };
}

function runSourceInventoryEnrichmentPlan(dependencies = {}) {
    const loaded = loadDependencies(dependencies);
    const inputGate = validateInputs(loaded.manifest, loaded.l2v3tArtifact);
    if (!inputGate.ok) return { ok: false, status: 3, errors: inputGate.errors };

    const inputPathAnalysis = analyzeInputPaths(INPUT_PATHS, dependencies);
    const artifact = buildArtifact({
        manifest: loaded.manifest,
        l2v3nArtifact: loaded.l2v3nArtifact,
        l2v3pArtifact: loaded.l2v3pArtifact,
        l2v3qArtifact: loaded.l2v3qArtifact,
        l2v3rArtifact: loaded.l2v3rArtifact,
        l2v3tArtifact: loaded.l2v3tArtifact,
        inputPathAnalysis,
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
        '  node scripts/ops/pageprops_v2_source_inventory_enrichment_plan.js --write-files=yes',
        '',
        'Safety:',
        '  L2V3U is a no-write source inventory enrichment planning phase.',
        '  It does not fetch network, write DB/raw/matches, accept mappings, accept baselines, or retry raw writes.',
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
    const result = runSourceInventoryEnrichmentPlan({ writeFiles: options.writeFiles });
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
                analyzed_inventory_path_count: result.artifact.analyzed_inventory_path_count,
                source_inventory_file_count: result.artifact.source_inventory_file_count,
                manifest_candidate_field_gap_count: result.artifact.manifest_candidate_field_gap_count,
                missing_source_page_url_count: result.artifact.missing_source_page_url_count,
                missing_page_url_base_count: result.artifact.missing_page_url_base_count,
                missing_url_fragment_external_id_count: result.artifact.missing_url_fragment_external_id_count,
                missing_source_record_key_count: result.artifact.missing_source_record_key_count,
                proposed_new_field_count: result.artifact.proposed_new_field_count,
                enrichment_strategy: result.artifact.enrichment_strategy,
                enrichment_confidence: result.artifact.enrichment_confidence,
                requires_followup_implementation: result.artifact.requires_followup_implementation,
                requires_target_regeneration: result.artifact.requires_target_regeneration,
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
    L2V3N_ARTIFACT_PATH,
    L2V3P_ARTIFACT_PATH,
    L2V3Q_ARTIFACT_PATH,
    L2V3R_ARTIFACT_PATH,
    L2V3T_ARTIFACT_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_PATH,
    NEXT_RECOMMENDED_STEP,
    NEXT_REQUIRED_STEP,
    PROPOSED_ENRICHMENT_FIELDS,
    parseArgs,
    validateCliOptions,
    buildFieldGapSummary,
    analyzeInputPaths,
    validateInputs,
    buildPersistencePlan,
    buildUsagePlan,
    buildArtifact,
    updateManifestMetadata,
    buildReport,
    runSourceInventoryEnrichmentPlan,
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
