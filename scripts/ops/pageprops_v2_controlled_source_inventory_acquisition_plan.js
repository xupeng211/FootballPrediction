#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3X';
const PHASE_NAME = 'controlled_no_write_source_inventory_acquisition_planning';
const ARTIFACT_STATUS = 'completed_no_write_controlled_source_inventory_acquisition_planning';
const GENERATED_AT = '2026-05-21T11:30:00Z';
const MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const L2V3W_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.source_inventory_acquisition_path_investigation.phase521l2v3w.json';
const L2V3V_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.source_inventory_enrichment_implementation.phase521l2v3v.json';
const L2V3U_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.source_inventory_enrichment_plan.phase521l2v3u.json';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.controlled_source_inventory_acquisition_plan.phase521l2v3x.json';
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3X.md';
const NEXT_RECOMMENDED_STEP = 'Phase 5.21L2V3Y: controlled no-write source inventory acquisition execution';
const NEXT_REQUIRED_STEP = 'controlled_no_write_source_inventory_acquisition_execution';
const PLANNED_SCOPE = 'ligue1_2025_2026_profile_001_current_50_candidates_metadata_only_source_inventory';
const PLANNED_ENDPOINT = '/api/data/leagues?id=53&season=20252026';

const INPUT_PATHS = Object.freeze([
    { key: 'manifest', path: MANIFEST_PATH, role: 'current_manifest' },
    { key: 'l2v3w_artifact', path: L2V3W_ARTIFACT_PATH, role: 'acquisition_path_investigation' },
    { key: 'l2v3w_report', path: 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3W.md', role: 'report' },
    { key: 'l2v3v_artifact', path: L2V3V_ARTIFACT_PATH, role: 'source_inventory_enrichment_implementation' },
    { key: 'l2v3u_artifact', path: L2V3U_ARTIFACT_PATH, role: 'source_inventory_enrichment_planning' },
    {
        key: 'source_inventory_preflight',
        path: 'scripts/ops/single_league_target_discovery_source_inventory_preflight.js',
        role: 'future_controlled_source_inventory_execution_candidate',
    },
    {
        key: 'source_inventory_adapter',
        path: 'src/infrastructure/services/FotMobSourceInventoryAdapter.js',
        role: 'metadata_extraction_adapter',
    },
    {
        key: 'small_batch_manifest_builder',
        path: 'scripts/ops/single_league_small_batch_target_manifest_plan.js',
        role: 'manifest_candidate_builder',
    },
    {
        key: 'source_inventory_acquisition_path_investigation',
        path: 'scripts/ops/pageprops_v2_source_inventory_acquisition_path_investigation.js',
        role: 'prior_no_write_investigation_helper',
    },
]);

const PLANNED_METADATA_FIELDS = Object.freeze([
    {
        field: 'source_page_url',
        source: 'source inventory pageUrl/matchUrl/href/equivalent URL field',
        required_for_future_target_regeneration: true,
    },
    {
        field: 'source_page_url_base',
        source: 'source_page_url with fragment removed',
        required_for_future_target_regeneration: true,
    },
    {
        field: 'source_url_fragment_external_id',
        source: 'fragment component of source_page_url when present',
        required_for_future_target_regeneration: true,
    },
    {
        field: 'source_slug',
        source: 'match route slug parsed from source_page_url path',
        required_for_future_target_regeneration: true,
    },
    {
        field: 'source_route_code',
        source: 'stable route code parsed from source_page_url path when present',
        required_for_future_target_regeneration: true,
    },
    {
        field: 'schedule_external_id',
        source: 'source inventory schedule-side match id',
        required_for_future_target_regeneration: true,
    },
    {
        field: 'schedule_date',
        source: 'source inventory schedule-side date/kickoff metadata',
        required_for_future_target_regeneration: true,
    },
    {
        field: 'schedule_home_team',
        source: 'source inventory schedule-side home team',
        required_for_future_target_regeneration: true,
    },
    {
        field: 'schedule_away_team',
        source: 'source inventory schedule-side away team',
        required_for_future_target_regeneration: true,
    },
    {
        field: 'source_inventory_record_key',
        source: 'deterministic source inventory record path plus external id',
        required_for_future_target_regeneration: true,
    },
    {
        field: 'source_inventory_generated_at',
        source: 'controlled acquisition execution timestamp',
        required_for_future_target_regeneration: true,
    },
    {
        field: 'identity_evidence_status',
        source: 'complete/partial/missing/unknown source URL identity evidence classification',
        required_for_future_target_regeneration: true,
    },
    {
        field: 'source_endpoint_summary',
        source: 'safe endpoint route summary without headers/cookies/tokens/body',
        required_for_future_target_regeneration: false,
    },
    {
        field: 'acquisition_status',
        source: 'metadata-only execution status for future acquisition run',
        required_for_future_target_regeneration: false,
    },
    {
        field: 'safe_error_summary',
        source: 'short sanitized error category without response body',
        required_for_future_target_regeneration: false,
    },
]);

const PAYLOAD_SAFETY_RULES = Object.freeze([
    'do_not_save_full_api_payload',
    'do_not_print_full_api_payload',
    'do_not_save_full_pageProps',
    'do_not_print_full_pageProps',
    'do_not_save_full_raw_data',
    'do_not_print_full_raw_data',
    'do_not_save_full_html_or_source_body',
    'do_not_print_full_html_or_source_body',
    'metadata_only_safe_fields_only',
    'do_not_record_cookies_tokens_headers',
    'stop_on_block_captcha_or_abnormal_response',
]);

const STOPPING_RULES = Object.freeze([
    'http_block_or_captcha_signal',
    'rate_limit_signal',
    'parse_failure_spike',
    'widespread_non_200_response',
    'unexpected_schema_drift',
    'payload_too_large_or_suspicious_small_payload',
    'source_identity_mismatch',
    'any_attempted_write_path',
    'browser_proxy_captcha_bypass_required',
    'full_payload_persistence_attempt',
]);

const PLANNED_OUTPUT_ARTIFACTS = Object.freeze([
    {
        artifact_type: 'metadata_only_source_inventory_artifact',
        planned_path:
            'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.controlled_source_inventory_acquisition.phase521l2v3y.json',
        full_payload_allowed: false,
    },
    {
        artifact_type: 'governance_report',
        planned_path: 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3Y.md',
        full_payload_allowed: false,
    },
    {
        artifact_type: 'manifest_metadata_update',
        planned_path: MANIFEST_PATH,
        full_payload_allowed: false,
    },
    {
        artifact_type: 'unit_test_fixture_or_fake_fetch',
        planned_path: 'tests/unit/pageprops_v2_controlled_source_inventory_acquisition_plan.test.js',
        full_payload_allowed: false,
    },
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

function fileExists(filePath, dependencies = {}) {
    if (dependencies.existingPaths instanceof Set) return dependencies.existingPaths.has(filePath);
    return fs.existsSync(absolutePath(filePath));
}

function analyzeInputs(inputPaths = INPUT_PATHS, dependencies = {}) {
    return inputPaths.map(item => ({
        key: item.key,
        path: item.path,
        role: item.role,
        exists: fileExists(item.path, dependencies),
    }));
}

function deriveLeagueId(manifest = {}) {
    return Number(manifest.league?.league_id || manifest.candidate_targets?.[0]?.league_id || 53);
}

function deriveSeason(manifest = {}) {
    return normalizeText(manifest.league?.season || manifest.candidate_targets?.[0]?.season || '2025/2026');
}

function validateInputs(manifest = {}, l2v3wArtifact = {}) {
    const errors = [];
    const alreadyCompleted =
        normalizeText(manifest.phase_5_21_l2v3x_planning_status) === ARTIFACT_STATUS &&
        normalizeText(manifest.controlled_source_inventory_acquisition_planning_status) === ARTIFACT_STATUS;

    if (!Array.isArray(manifest.candidate_targets) || manifest.candidate_targets.length !== 50) {
        errors.push('manifest candidate_targets must contain 50 targets');
    }
    if (
        normalizeText(manifest.next_required_step) !== 'controlled_no_write_source_inventory_acquisition_planning' &&
        !alreadyCompleted
    ) {
        errors.push('manifest next_required_step must be controlled_no_write_source_inventory_acquisition_planning');
    }
    if (manifest.raw_write_ready_for_execution !== false) {
        errors.push('manifest raw_write_ready_for_execution must remain false');
    }
    if (Number(manifest.accepted_mapping_count || 0) !== 0) {
        errors.push('manifest accepted_mapping_count must remain 0');
    }
    if (normalizeText(l2v3wArtifact.proposal_phase) !== 'Phase 5.21L2V3W') {
        errors.push('L2V3W artifact must be present');
    }
    if (l2v3wArtifact.live_source_check_performed !== false) {
        errors.push('L2V3W live_source_check_performed must remain false');
    }
    if (l2v3wArtifact.network_request_performed !== false) {
        errors.push('L2V3W network_request_performed must remain false');
    }
    if (l2v3wArtifact.source_inventory_contains_url_field !== false) {
        errors.push('L2V3W source_inventory_contains_url_field must remain false');
    }
    if (l2v3wArtifact.current_candidates_retroactively_enrichable !== false) {
        errors.push('L2V3W current_candidates_retroactively_enrichable must remain false');
    }
    if (l2v3wArtifact.requires_controlled_no_write_source_acquisition !== true) {
        errors.push('L2V3W requires_controlled_no_write_source_acquisition must remain true');
    }
    if (Number(l2v3wArtifact.accepted_mapping_count || 0) !== 0) {
        errors.push('L2V3W accepted_mapping_count must remain 0');
    }
    if (l2v3wArtifact.raw_write_ready_for_execution !== false) {
        errors.push('L2V3W raw_write_ready_for_execution must remain false');
    }
    return { ok: errors.length === 0, errors };
}

function buildAcquisitionScope(manifest = {}) {
    return {
        planned_acquisition_scope: PLANNED_SCOPE,
        league_id: deriveLeagueId(manifest),
        league_name: normalizeText(
            manifest.league?.league_name || manifest.candidate_targets?.[0]?.league_name || 'Ligue 1'
        ),
        season: deriveSeason(manifest),
        candidate_scope_count: Array.isArray(manifest.candidate_targets) ? manifest.candidate_targets.length : 0,
        include_known_completed_seeded_targets: false,
        exclude_known_completed_seeded_targets: true,
        source_inventory_only: true,
        raw_match_data_generation_allowed: false,
        target_generation_allowed_after_review: true,
    };
}

function buildArtifact({
    manifest = {},
    l2v3wArtifact = {},
    l2v3vArtifact = {},
    l2v3uArtifact = {},
    inputAnalysis = [],
    generatedAt = GENERATED_AT,
} = {}) {
    const scope = buildAcquisitionScope(manifest);
    const plannedTargetLeagueId = scope.league_id;
    const plannedTargetSeason = scope.season;

    return {
        artifact_type: 'controlled_source_inventory_acquisition_plan',
        artifact_status: ARTIFACT_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        source_phase: 'Phase 5.21L2V3W',
        generated_at: generatedAt,
        no_write: true,
        live_fetch_performed: false,
        live_source_check_performed: false,
        source_acquisition_execution_performed: false,
        network_request_performed: false,
        db_write_performed: false,
        raw_insert_performed: false,
        raw_match_data_insert_performed: false,
        matches_write_performed: false,
        matches_external_id_modified: false,
        schema_migration_performed: false,
        parser_features_training_prediction_performed: false,
        browser_proxy_captcha_bypass_performed: false,
        bulk_crawl_spider_performed: false,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        baseline_replacement_accepted: false,
        raw_write_authorization_performed: false,
        raw_write_retry_performed: false,
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
        planned_acquisition_scope: scope.planned_acquisition_scope,
        planned_source_endpoint: PLANNED_ENDPOINT,
        planned_target_league_id: plannedTargetLeagueId,
        planned_target_season: plannedTargetSeason,
        planned_candidate_scope_count: scope.candidate_scope_count,
        planned_metadata_field_count: PLANNED_METADATA_FIELDS.length,
        planned_output_artifact_count: PLANNED_OUTPUT_ARTIFACTS.length,
        acquisition_execution_authorization_required: true,
        baseline_acceptance_required: true,
        final_db_write_authorization_required: true,
        planned_scope_details: scope,
        planned_metadata_fields: PLANNED_METADATA_FIELDS,
        payload_safety_rules: PAYLOAD_SAFETY_RULES,
        stopping_rules: STOPPING_RULES,
        planned_output_artifacts: PLANNED_OUTPUT_ARTIFACTS,
        input_analysis: inputAnalysis,
        upstream_context: {
            l2v3w_requires_controlled_no_write_source_acquisition:
                l2v3wArtifact.requires_controlled_no_write_source_acquisition ?? null,
            l2v3w_source_inventory_contains_url_field: l2v3wArtifact.source_inventory_contains_url_field ?? null,
            l2v3w_current_candidates_retroactively_enrichable:
                l2v3wArtifact.current_candidates_retroactively_enrichable ?? null,
            l2v3v_identity_evidence_missing_count: l2v3vArtifact.identity_evidence_missing_count ?? null,
            l2v3u_missing_source_page_url_count: l2v3uArtifact.missing_source_page_url_count ?? null,
        },
        safety_contract: {
            controlled_acquisition_plan_is_not_accepted_mapping: true,
            controlled_acquisition_plan_is_not_raw_write_authorization: true,
            controlled_acquisition_plan_is_not_baseline_acceptance: true,
            controlled_acquisition_plan_is_not_source_acquisition_execution: true,
            source_inventory_acquisition_execution_requires_separate_authorization: true,
            missing_source_url_evidence_remains_blocker: true,
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
        phase_5_21_l2v3x_planning_status: artifact.artifact_status,
        controlled_source_inventory_acquisition_planning_status: artifact.artifact_status,
        phase_5_21_l2v3x_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3x_report_path: REPORT_PATH,
        planned_acquisition_scope: artifact.planned_acquisition_scope,
        phase_5_21_l2v3x_planned_acquisition_scope: artifact.planned_acquisition_scope,
        planned_source_endpoint: artifact.planned_source_endpoint,
        phase_5_21_l2v3x_planned_source_endpoint: artifact.planned_source_endpoint,
        planned_target_league_id: artifact.planned_target_league_id,
        phase_5_21_l2v3x_planned_target_league_id: artifact.planned_target_league_id,
        planned_target_season: artifact.planned_target_season,
        phase_5_21_l2v3x_planned_target_season: artifact.planned_target_season,
        planned_candidate_scope_count: artifact.planned_candidate_scope_count,
        phase_5_21_l2v3x_planned_candidate_scope_count: artifact.planned_candidate_scope_count,
        planned_metadata_field_count: artifact.planned_metadata_field_count,
        phase_5_21_l2v3x_planned_metadata_field_count: artifact.planned_metadata_field_count,
        planned_output_artifact_count: artifact.planned_output_artifact_count,
        phase_5_21_l2v3x_planned_output_artifact_count: artifact.planned_output_artifact_count,
        live_fetch_performed: false,
        db_write_performed: false,
        phase_5_21_l2v3x_live_fetch_performed: false,
        phase_5_21_l2v3x_db_write_performed: false,
        accepted_mapping_count: 0,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        phase_5_21_l2v3x_accepted_mapping_count: 0,
        phase_5_21_l2v3x_identity_mapping_acceptance_performed: false,
        phase_5_21_l2v3x_baseline_acceptance_performed: false,
        phase_5_21_l2v3x_raw_write_retry_performed: false,
        phase_5_21_l2v3x_raw_write_ready_for_execution: false,
        requires_separate_source_inventory_acquisition_execution: true,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

function buildReport(artifact = {}) {
    return `# Data Entrypoint Governance - Phase 5.21 L2V3X

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- no_write=true
- live_fetch_performed=false
- source_acquisition_execution_performed=false
- network_request_performed=false
- db_write_performed=false
- raw_insert_performed=false
- matches_write_performed=false
- matches_external_id_modified=false
- schema_migration_performed=false
- parser_features_training_prediction_performed=false
- browser_proxy_captcha_bypass_performed=false

## Classification Output

- planned_acquisition_scope=${artifact.planned_acquisition_scope}
- planned_source_endpoint=${artifact.planned_source_endpoint}
- planned_target_league_id=${artifact.planned_target_league_id}
- planned_target_season=${artifact.planned_target_season}
- planned_candidate_scope_count=${artifact.planned_candidate_scope_count}
- planned_metadata_field_count=${artifact.planned_metadata_field_count}
- planned_output_artifact_count=${artifact.planned_output_artifact_count}
- live_fetch_performed=false
- db_write_performed=false
- raw_write_ready_for_execution=false
- accepted_mapping_count=0
- acquisition_execution_authorization_required=true
- baseline_acceptance_required=true
- final_db_write_authorization_required=true
- recommended_next_step=${artifact.recommended_next_step}

## Planned Acquisition Scope

- source=FotMob league source inventory route
- endpoint_summary=${artifact.planned_source_endpoint}
- league_id=${artifact.planned_target_league_id}
- season=${artifact.planned_target_season}
- candidate_scope=current 50 manifest candidates for profile_001
- known completed seeded targets remain excluded from new raw acquisition scope
- output is source inventory metadata only; it must not generate raw_match_data rows

## Planned Metadata-Only Fields

${artifact.planned_metadata_fields.map(item => `- ${item.field}: ${item.source}`).join('\n')}

## Payload Safety Rules

${artifact.payload_safety_rules.map(item => `- ${item}`).join('\n')}

## Stopping Rules

${artifact.stopping_rules.map(item => `- ${item}`).join('\n')}

## Output Artifacts

${artifact.planned_output_artifacts.map(item => `- ${item.artifact_type}: ${item.planned_path}`).join('\n')}

## Safety Contract

- controlled acquisition plan is not accepted mapping.
- controlled acquisition plan is not raw write authorization.
- controlled acquisition plan is not baseline acceptance.
- controlled acquisition plan does not execute live fetch.
- source inventory acquisition execution requires separate authorization.
- missing source URL evidence remains blocked.
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
        l2v3wArtifact: dependencies.l2v3wArtifact || readJsonFile(L2V3W_ARTIFACT_PATH),
        l2v3vArtifact: dependencies.l2v3vArtifact || readJsonFile(L2V3V_ARTIFACT_PATH),
        l2v3uArtifact: dependencies.l2v3uArtifact || readJsonFile(L2V3U_ARTIFACT_PATH),
    };
}

function runControlledSourceInventoryAcquisitionPlan(dependencies = {}) {
    const loaded = loadDependencies(dependencies);
    const inputGate = validateInputs(loaded.manifest, loaded.l2v3wArtifact);
    if (!inputGate.ok) return { ok: false, status: 3, errors: inputGate.errors };

    const inputAnalysis = dependencies.inputAnalysis || analyzeInputs(INPUT_PATHS, dependencies);
    const artifact = buildArtifact({
        ...loaded,
        inputAnalysis,
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
        '  node scripts/ops/pageprops_v2_controlled_source_inventory_acquisition_plan.js --write-files=yes',
        '',
        'Safety:',
        '  L2V3X is a no-write planning phase.',
        '  It does not fetch live source inventory, write DB/raw/matches, accept mappings, accept baselines, or retry raw writes.',
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
    const result = runControlledSourceInventoryAcquisitionPlan({ writeFiles: options.writeFiles });
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
                planned_acquisition_scope: result.artifact.planned_acquisition_scope,
                planned_source_endpoint: result.artifact.planned_source_endpoint,
                planned_target_league_id: result.artifact.planned_target_league_id,
                planned_target_season: result.artifact.planned_target_season,
                planned_candidate_scope_count: result.artifact.planned_candidate_scope_count,
                planned_metadata_field_count: result.artifact.planned_metadata_field_count,
                planned_output_artifact_count: result.artifact.planned_output_artifact_count,
                live_fetch_performed: result.artifact.live_fetch_performed,
                db_write_performed: result.artifact.db_write_performed,
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
    L2V3W_ARTIFACT_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_PATH,
    INPUT_PATHS,
    PLANNED_METADATA_FIELDS,
    PAYLOAD_SAFETY_RULES,
    STOPPING_RULES,
    PLANNED_OUTPUT_ARTIFACTS,
    parseArgs,
    validateCliOptions,
    analyzeInputs,
    validateInputs,
    buildAcquisitionScope,
    buildArtifact,
    updateManifestMetadata,
    buildReport,
    runControlledSourceInventoryAcquisitionPlan,
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
