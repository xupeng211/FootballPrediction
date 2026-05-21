#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3W';
const PHASE_NAME = 'source_inventory_acquisition_path_investigation';
const ARTIFACT_STATUS = 'completed_no_write_source_inventory_acquisition_path_investigation';
const GENERATED_AT = '2026-05-21T10:30:00Z';
const MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const L2V3V_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.source_inventory_enrichment_implementation.phase521l2v3v.json';
const L2V3U_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.source_inventory_enrichment_plan.phase521l2v3u.json';
const L2V3T_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.continued_detail_endpoint_investigation.phase521l2v3t.json';
const L2V3R_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.detail_url_construction_fix_plan.phase521l2v3r.json';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.source_inventory_acquisition_path_investigation.phase521l2v3w.json';
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3W.md';
const NEXT_RECOMMENDED_STEP = 'Phase 5.21L2V3X: controlled no-write source inventory acquisition planning';
const NEXT_REQUIRED_STEP = 'controlled_no_write_source_inventory_acquisition_planning';
const RECOMMENDED_STRATEGY = 'controlled_no_write_source_inventory_acquisition_planning';

const SOURCE_INVENTORY_INPUT_PATHS = Object.freeze([
    { key: 'manifest', path: MANIFEST_PATH, role: 'current_manifest' },
    { key: 'l2v3v_artifact', path: L2V3V_ARTIFACT_PATH, role: 'source_inventory_enrichment_implementation' },
    { key: 'l2v3u_artifact', path: L2V3U_ARTIFACT_PATH, role: 'source_inventory_enrichment_planning' },
    { key: 'l2v3t_artifact', path: L2V3T_ARTIFACT_PATH, role: 'continued_detail_endpoint_investigation' },
    { key: 'l2v3r_artifact', path: L2V3R_ARTIFACT_PATH, role: 'detail_url_construction_plan' },
]);

const ACQUISITION_PATHS = Object.freeze([
    {
        key: 'source_inventory_adapter',
        path: 'src/infrastructure/services/FotMobSourceInventoryAdapter.js',
        role: 'extracts source inventory match identity and URL evidence when present',
    },
    {
        key: 'source_inventory_preflight',
        path: 'scripts/ops/single_league_target_discovery_source_inventory_preflight.js',
        role: 'authorized source inventory acquisition and manifest candidate generation',
    },
    {
        key: 'small_batch_manifest_builder',
        path: 'scripts/ops/single_league_small_batch_target_manifest_plan.js',
        role: 'local DB backed manifest proposal builder',
    },
    {
        key: 'source_inventory_enrichment_apply',
        path: 'scripts/ops/pageprops_v2_source_inventory_enrichment_apply.js',
        role: 'source-controlled manifest enrichment helper',
    },
    {
        key: 'source_inventory_enrichment_plan',
        path: 'scripts/ops/pageprops_v2_source_inventory_enrichment_plan.js',
        role: 'L2V3U enrichment planning helper',
    },
    {
        key: 'l1_discovery_safe_preview',
        path: 'scripts/ops/l1_discovery_safe_preview.js',
        role: 'L1 safe discovery preview entrypoint',
    },
    {
        key: 'fixture_harvester_l1',
        path: 'scripts/ops/fixture_harvester_l1.js',
        role: 'legacy L1 fixture harvest code path for read-only audit only',
    },
    {
        key: 'discovery_parser',
        path: 'src/infrastructure/services/DiscoveryParser.js',
        role: 'L1 fixture parser used by source inventory adapter',
    },
    {
        key: 'l1_config_manager',
        path: 'src/infrastructure/services/L1ConfigManager.js',
        role: 'FotMob league API URL construction',
    },
    {
        key: 'source_inventory_preflight_test',
        path: 'tests/unit/single_league_target_discovery_source_inventory_preflight.test.js',
        role: 'source inventory URL evidence propagation tests',
    },
    {
        key: 'source_inventory_adapter_test',
        path: 'tests/unit/FotMobSourceInventoryAdapter.test.js',
        role: 'adapter URL evidence extraction tests',
    },
]);

const SOURCE_URL_FIELDS = Object.freeze([
    'source_page_url',
    'pageUrl',
    'page_url',
    'matchUrl',
    'match_url',
    'href',
    'source_url',
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

function loadTextByPath(filePath, dependencies = {}) {
    if (
        dependencies.sourceTextByPath &&
        Object.prototype.hasOwnProperty.call(dependencies.sourceTextByPath, filePath)
    ) {
        return dependencies.sourceTextByPath[filePath];
    }
    return readTextFile(filePath);
}

function fileExists(filePath, dependencies = {}) {
    if (
        dependencies.sourceTextByPath &&
        Object.prototype.hasOwnProperty.call(dependencies.sourceTextByPath, filePath)
    ) {
        return true;
    }
    return fs.existsSync(absolutePath(filePath));
}

function analyzeAcquisitionPaths(dependencies = {}) {
    return ACQUISITION_PATHS.filter(item => fileExists(item.path, dependencies)).map(item => {
        const text = loadTextByPath(item.path, dependencies);
        return {
            key: item.key,
            path: item.path,
            role: item.role,
            extracts_or_mentions_url_field: /source_page_url|pageUrl|page_url|matchUrl|match_url|href/.test(text),
            propagates_record_key: /source_inventory_record_key/.test(text),
            imports_network_or_db_module: /\brequire\(['"](pg|http|https|playwright|puppeteer)['"]\)/.test(text),
        };
    });
}

function countUrlEvidence(targets = []) {
    return {
        target_count: targets.length,
        source_page_url_count: targets.filter(target => normalizeText(target.source_page_url)).length,
        source_page_url_base_count: targets.filter(target => normalizeText(target.source_page_url_base)).length,
        source_url_fragment_external_id_count: targets.filter(target =>
            normalizeText(target.source_url_fragment_external_id)
        ).length,
        source_inventory_record_key_count: targets.filter(target => normalizeText(target.source_inventory_record_key))
            .length,
        identity_evidence_missing_count: targets.filter(
            target => normalizeText(target.identity_evidence_status) === 'missing'
        ).length,
    };
}

function hasCandidateUrlEvidenceValue(target = {}) {
    return SOURCE_URL_FIELDS.some(field => {
        const value = normalizeText(target[field]);
        if (!value) return false;
        if (field === 'source_url' && /api\/data\/leagues/i.test(value)) return false;
        return true;
    });
}

function sourceInventoryContainsCandidateUrlField(manifest = {}) {
    const targets = Array.isArray(manifest.candidate_targets) ? manifest.candidate_targets : [];
    return targets.some(hasCandidateUrlEvidenceValue);
}

function buildCodeCapabilitySummary(acquisitionPathAnalysis = []) {
    const byKey = Object.fromEntries(acquisitionPathAnalysis.map(item => [item.key, item]));
    const adapterText = byKey.source_inventory_adapter || {};
    const preflightText = byKey.source_inventory_preflight || {};
    const smallBatchText = byKey.small_batch_manifest_builder || {};

    return {
        adapter_extracts_url_field: Boolean(
            adapterText.extracts_or_mentions_url_field && adapterText.propagates_record_key
        ),
        manifest_builder_propagates_url_field: Boolean(
            preflightText.extracts_or_mentions_url_field &&
            preflightText.propagates_record_key &&
            smallBatchText.extracts_or_mentions_url_field &&
            smallBatchText.propagates_record_key
        ),
        l1_discovery_captures_url_field: Boolean(
            adapterText.extracts_or_mentions_url_field && preflightText.extracts_or_mentions_url_field
        ),
    };
}

function validateInputs(manifest = {}, l2v3vArtifact = {}) {
    const errors = [];
    const alreadyCompleted =
        normalizeText(manifest.phase_5_21_l2v3w_investigation_status) === ARTIFACT_STATUS &&
        normalizeText(manifest.source_inventory_acquisition_path_investigation_status) === ARTIFACT_STATUS;
    if (!Array.isArray(manifest.candidate_targets) || manifest.candidate_targets.length !== 50) {
        errors.push('manifest candidate_targets must contain 50 targets');
    }
    if (
        normalizeText(manifest.next_required_step) !== 'source_inventory_acquisition_path_investigation' &&
        !alreadyCompleted
    ) {
        errors.push('manifest next_required_step must be source_inventory_acquisition_path_investigation');
    }
    if (manifest.raw_write_ready_for_execution !== false) {
        errors.push('manifest raw_write_ready_for_execution must remain false');
    }
    if (Number(manifest.accepted_mapping_count || 0) !== 0) {
        errors.push('manifest accepted_mapping_count must remain 0');
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
    if (Number(l2v3vArtifact.identity_evidence_missing_count || 0) !== 50) {
        errors.push('L2V3V identity_evidence_missing_count must remain 50');
    }
    return { ok: errors.length === 0, errors };
}

function buildArtifact({
    manifest = {},
    l2v3vArtifact = {},
    l2v3uArtifact = {},
    l2v3tArtifact = {},
    l2v3rArtifact = {},
    generatedAt = GENERATED_AT,
    dependencies = {},
} = {}) {
    const candidateTargets = Array.isArray(manifest.candidate_targets) ? manifest.candidate_targets : [];
    const urlCounts = countUrlEvidence(candidateTargets);
    const acquisitionPathAnalysis = analyzeAcquisitionPaths(dependencies);
    const codeCapabilities = buildCodeCapabilitySummary(acquisitionPathAnalysis);
    const sourceInventoryContainsUrlField = sourceInventoryContainsCandidateUrlField(manifest);
    const currentCandidatesRetroactivelyEnrichable =
        sourceInventoryContainsUrlField &&
        urlCounts.source_page_url_count > 0 &&
        urlCounts.source_inventory_record_key_count > 0;

    return {
        artifact_type: 'source_inventory_acquisition_path_investigation',
        artifact_status: ARTIFACT_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        source_phase: 'Phase 5.21L2V3V',
        generated_at: generatedAt,
        no_write: true,
        live_source_check_performed: false,
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
        baseline_replacement_accepted: false,
        raw_write_authorization_performed: false,
        raw_write_retry_performed: false,
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
        analyzed_acquisition_path_count: acquisitionPathAnalysis.length,
        source_inventory_input_file_count: SOURCE_INVENTORY_INPUT_PATHS.length,
        source_inventory_contains_url_field: sourceInventoryContainsUrlField,
        adapter_extracts_url_field: codeCapabilities.adapter_extracts_url_field,
        manifest_builder_propagates_url_field: codeCapabilities.manifest_builder_propagates_url_field,
        l1_discovery_captures_url_field: codeCapabilities.l1_discovery_captures_url_field,
        current_candidates_retroactively_enrichable: currentCandidatesRetroactivelyEnrichable,
        requires_source_inventory_regeneration: !currentCandidatesRetroactivelyEnrichable,
        requires_l1_discovery_rerun: 'unknown',
        requires_controlled_no_write_source_acquisition: !sourceInventoryContainsUrlField,
        recommended_strategy: RECOMMENDED_STRATEGY,
        strategy_confidence: 'medium',
        current_candidate_url_evidence_counts: urlCounts,
        acquisition_path_analysis: acquisitionPathAnalysis,
        source_inventory_input_files: SOURCE_INVENTORY_INPUT_PATHS,
        source_inventory_acquisition_pipeline: [
            'FotMobSourceInventoryAdapter builds /api/data/leagues?id={leagueId}&season={season}.',
            'single_league_target_discovery_source_inventory_preflight can perform an authorized source inventory request and normalize discovered match objects.',
            'FotMobSourceInventoryAdapter now extracts pageUrl/matchUrl/href/url/link when present and derives base, fragment external_id, slug, route code, and record key.',
            'single_league_small_batch_target_manifest_plan is local DB backed and cannot recover pageUrl evidence absent from DB/local rows.',
            'pageprops_v2_source_inventory_enrichment_apply only enriches fields already present in source-controlled manifest candidates.',
        ],
        why_current_50_candidates_missing_url_evidence: [
            'current source-controlled manifest candidate targets have source_page_url/source_page_url_base/source_url_fragment_external_id/source_inventory_record_key set to null',
            'current source-controlled files preserve source_inventory_result summary metadata but not the full source inventory JSON body',
            'L2V3V enrichment implementation intentionally did not fabricate pageUrl, fragment id, route code, or source record key',
            'old manifest candidates cannot be retroactively enriched without a source-controlled source inventory record containing requested-side URL evidence',
        ],
        upstream_context: {
            l2v3v_candidate_targets_checked: l2v3vArtifact.candidate_targets_checked ?? null,
            l2v3v_identity_evidence_missing_count: l2v3vArtifact.identity_evidence_missing_count ?? null,
            l2v3u_missing_source_page_url_count: l2v3uArtifact.missing_source_page_url_count ?? null,
            l2v3t_previous_endpoint_status: l2v3tArtifact.previous_endpoint_status ?? null,
            l2v3t_precise_detail_endpoint_found: l2v3tArtifact.precise_detail_endpoint_found ?? null,
            l2v3r_uses_source_inventory_page_url: l2v3rArtifact.uses_source_inventory_page_url ?? null,
        },
        safety_contract: {
            acquisition_investigation_result_is_not_accepted_mapping: true,
            acquisition_investigation_result_is_not_raw_write_authorization: true,
            missing_source_url_evidence_remains_blocker: true,
            current_candidates_cannot_be_raw_write_ready_from_investigation_alone: true,
            no_live_fetch_performed: true,
            no_full_raw_data_pageprops_or_source_body_saved_or_printed: true,
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
        phase_5_21_l2v3w_investigation_status: artifact.artifact_status,
        source_inventory_acquisition_path_investigation_status: artifact.artifact_status,
        phase_5_21_l2v3w_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3w_report_path: REPORT_PATH,
        analyzed_acquisition_path_count: artifact.analyzed_acquisition_path_count,
        phase_5_21_l2v3w_analyzed_acquisition_path_count: artifact.analyzed_acquisition_path_count,
        source_inventory_input_file_count: artifact.source_inventory_input_file_count,
        phase_5_21_l2v3w_source_inventory_input_file_count: artifact.source_inventory_input_file_count,
        source_inventory_contains_url_field: artifact.source_inventory_contains_url_field,
        adapter_extracts_url_field: artifact.adapter_extracts_url_field,
        manifest_builder_propagates_url_field: artifact.manifest_builder_propagates_url_field,
        l1_discovery_captures_url_field: artifact.l1_discovery_captures_url_field,
        current_candidates_retroactively_enrichable: artifact.current_candidates_retroactively_enrichable,
        requires_source_inventory_regeneration: artifact.requires_source_inventory_regeneration,
        requires_l1_discovery_rerun: artifact.requires_l1_discovery_rerun,
        requires_controlled_no_write_source_acquisition: artifact.requires_controlled_no_write_source_acquisition,
        phase_5_21_l2v3w_source_inventory_contains_url_field: artifact.source_inventory_contains_url_field,
        phase_5_21_l2v3w_adapter_extracts_url_field: artifact.adapter_extracts_url_field,
        phase_5_21_l2v3w_manifest_builder_propagates_url_field: artifact.manifest_builder_propagates_url_field,
        phase_5_21_l2v3w_l1_discovery_captures_url_field: artifact.l1_discovery_captures_url_field,
        phase_5_21_l2v3w_current_candidates_retroactively_enrichable:
            artifact.current_candidates_retroactively_enrichable,
        phase_5_21_l2v3w_requires_source_inventory_regeneration: artifact.requires_source_inventory_regeneration,
        phase_5_21_l2v3w_requires_l1_discovery_rerun: artifact.requires_l1_discovery_rerun,
        phase_5_21_l2v3w_requires_controlled_no_write_source_acquisition:
            artifact.requires_controlled_no_write_source_acquisition,
        recommended_strategy: artifact.recommended_strategy,
        phase_5_21_l2v3w_recommended_strategy: artifact.recommended_strategy,
        strategy_confidence: artifact.strategy_confidence,
        phase_5_21_l2v3w_strategy_confidence: artifact.strategy_confidence,
        accepted_mapping_count: 0,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        phase_5_21_l2v3w_accepted_mapping_count: 0,
        phase_5_21_l2v3w_identity_mapping_acceptance_performed: false,
        phase_5_21_l2v3w_baseline_acceptance_performed: false,
        phase_5_21_l2v3w_raw_write_retry_performed: false,
        phase_5_21_l2v3w_raw_write_ready_for_execution: false,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

function buildReport(artifact = {}) {
    return `# Data Entrypoint Governance - Phase 5.21 L2V3W

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- no_write=true
- live_source_check_performed=false
- network_request_performed=false
- db_write_performed=false
- raw_insert_performed=false
- matches_write_performed=false
- matches_external_id_modified=false
- schema_migration_performed=false
- parser_features_training_prediction_performed=false
- browser_proxy_captcha_bypass_performed=false

## Classification Output

- analyzed_acquisition_path_count=${artifact.analyzed_acquisition_path_count}
- source_inventory_input_file_count=${artifact.source_inventory_input_file_count}
- source_inventory_contains_url_field=${artifact.source_inventory_contains_url_field}
- adapter_extracts_url_field=${artifact.adapter_extracts_url_field}
- manifest_builder_propagates_url_field=${artifact.manifest_builder_propagates_url_field}
- l1_discovery_captures_url_field=${artifact.l1_discovery_captures_url_field}
- current_candidates_retroactively_enrichable=${artifact.current_candidates_retroactively_enrichable}
- requires_source_inventory_regeneration=${artifact.requires_source_inventory_regeneration}
- requires_l1_discovery_rerun=${artifact.requires_l1_discovery_rerun}
- requires_controlled_no_write_source_acquisition=${artifact.requires_controlled_no_write_source_acquisition}
- recommended_strategy=${artifact.recommended_strategy}
- strategy_confidence=${artifact.strategy_confidence}
- accepted_mapping_count=0
- raw_write_ready_for_execution=false

## Data Flow Conclusion

- The current source inventory path is the FotMob league source inventory route: /api/data/leagues?id={leagueId}&season={season}.
- The source inventory adapter and source inventory preflight now support source_page_url, source_page_url_base, source_url_fragment_external_id, source_slug, source_route_code, and source_inventory_record_key when those values are present in source-controlled metadata.
- The local DB backed small-batch manifest builder cannot recover requested-side pageUrl evidence from DB rows because matches/raw row counts do not carry source inventory pageUrl or fragment metadata.
- The current committed manifest preserves candidate targets and a source_inventory_result summary, but it does not preserve the full source inventory JSON body or per-record pageUrl evidence.
- Therefore the current 50 candidates are not retroactively enrichable from source-controlled files currently in the repository.

## Current 50 Candidate URL Evidence

- candidate_targets_checked=${artifact.current_candidate_url_evidence_counts.target_count}
- candidate_targets_with_source_page_url=${artifact.current_candidate_url_evidence_counts.source_page_url_count}
- candidate_targets_with_source_page_url_base=${artifact.current_candidate_url_evidence_counts.source_page_url_base_count}
- candidate_targets_with_source_url_fragment_external_id=${artifact.current_candidate_url_evidence_counts.source_url_fragment_external_id_count}
- candidate_targets_with_source_inventory_record_key=${artifact.current_candidate_url_evidence_counts.source_inventory_record_key_count}
- identity_evidence_missing_count=${artifact.current_candidate_url_evidence_counts.identity_evidence_missing_count}

## Why Missing

${artifact.why_current_50_candidates_missing_url_evidence.map(item => `- ${item}`).join('\n')}

## Safety Contract

- acquisition investigation result is not accepted mapping.
- acquisition investigation result is not raw write authorization.
- missing source URL evidence remains a blocker.
- current candidates cannot become raw-write-ready from investigation alone.
- no live fetch was performed.
- no full raw_data, pageProps, or source body was saved or printed.
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
        l2v3vArtifact: dependencies.l2v3vArtifact || readJsonFile(L2V3V_ARTIFACT_PATH),
        l2v3uArtifact: dependencies.l2v3uArtifact || readJsonFile(L2V3U_ARTIFACT_PATH),
        l2v3tArtifact: dependencies.l2v3tArtifact || readJsonFile(L2V3T_ARTIFACT_PATH),
        l2v3rArtifact: dependencies.l2v3rArtifact || readJsonFile(L2V3R_ARTIFACT_PATH),
    };
}

function runSourceInventoryAcquisitionPathInvestigation(dependencies = {}) {
    const loaded = loadDependencies(dependencies);
    const inputGate = validateInputs(loaded.manifest, loaded.l2v3vArtifact);
    if (!inputGate.ok) return { ok: false, status: 3, errors: inputGate.errors };

    const artifact = buildArtifact({
        ...loaded,
        generatedAt: dependencies.generatedAt || GENERATED_AT,
        dependencies,
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
        '  node scripts/ops/pageprops_v2_source_inventory_acquisition_path_investigation.js --write-files=yes',
        '',
        'Safety:',
        '  L2V3W is a no-write source inventory acquisition path investigation phase.',
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
    const result = runSourceInventoryAcquisitionPathInvestigation({ writeFiles: options.writeFiles });
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
                analyzed_acquisition_path_count: result.artifact.analyzed_acquisition_path_count,
                source_inventory_input_file_count: result.artifact.source_inventory_input_file_count,
                source_inventory_contains_url_field: result.artifact.source_inventory_contains_url_field,
                adapter_extracts_url_field: result.artifact.adapter_extracts_url_field,
                manifest_builder_propagates_url_field: result.artifact.manifest_builder_propagates_url_field,
                l1_discovery_captures_url_field: result.artifact.l1_discovery_captures_url_field,
                current_candidates_retroactively_enrichable:
                    result.artifact.current_candidates_retroactively_enrichable,
                requires_source_inventory_regeneration: result.artifact.requires_source_inventory_regeneration,
                requires_l1_discovery_rerun: result.artifact.requires_l1_discovery_rerun,
                requires_controlled_no_write_source_acquisition:
                    result.artifact.requires_controlled_no_write_source_acquisition,
                recommended_strategy: result.artifact.recommended_strategy,
                strategy_confidence: result.artifact.strategy_confidence,
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
    L2V3V_ARTIFACT_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_PATH,
    ACQUISITION_PATHS,
    SOURCE_INVENTORY_INPUT_PATHS,
    parseArgs,
    validateCliOptions,
    analyzeAcquisitionPaths,
    countUrlEvidence,
    sourceInventoryContainsCandidateUrlField,
    buildCodeCapabilitySummary,
    validateInputs,
    buildArtifact,
    updateManifestMetadata,
    buildReport,
    runSourceInventoryAcquisitionPathInvestigation,
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
