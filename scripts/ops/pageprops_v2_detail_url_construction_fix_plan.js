#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3R';
const PHASE_NAME = 'detail_url_construction_fix_planning';
const ARTIFACT_STATUS = 'completed_no_write_detail_url_construction_fix_planning';
const GENERATED_AT = '2026-05-20T00:00:00Z';
const MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const L2V3Q_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.continued_metadata_investigation.phase521l2v3q.json';
const L2V3Q_REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3Q.md';
const L2V3P_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.metadata_only_detail_check.phase521l2v3p.json';
const L2V3N_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.expanded_date_rule_verification.phase521l2v3n.json';
const L2V3M_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.date_mismatch_rule_implementation.phase521l2v3m.json';
const L2V3E_REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3E.md';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.detail_url_construction_fix_plan.phase521l2v3r.json';
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3R.md';
const NEXT_RECOMMENDED_STEP = 'Phase 5.21L2V3S: detail API endpoint feasibility verification';
const NEXT_REQUIRED_STEP = 'detail_api_endpoint_feasibility_verification';

const SOURCE_FILES = Object.freeze([
    {
        key: 'fotmob_raw_detail_fetcher',
        path: 'src/infrastructure/services/FotMobRawDetailFetcher.js',
        routePattern: 'new URL(`/match/${id}`, FOTMOB_BASE_URL)',
        sourceInventoryPattern: 'buildDetailRequestFromSourceInventoryPageUrl(',
    },
    {
        key: 'metadata_only_detail_check',
        path: 'scripts/ops/pageprops_v2_metadata_only_detail_check.js',
        routePattern: 'buildFotMobMatchUrl(externalId)',
        sourceInventoryPattern: 'buildDetailRequestFromSourceInventoryPageUrl(',
    },
    {
        key: 'single_league_small_batch_preflight',
        path: 'scripts/ops/single_league_small_batch_pageprops_v2_preflight.js',
        routePattern: 'buildFotMobMatchUrl(target.external_id)',
        sourceInventoryPattern: 'buildDetailRequestFromSourceInventoryPageUrl(',
    },
    {
        key: 'single_league_controlled_write_execute',
        path: 'scripts/ops/single_league_pageprops_v2_controlled_write_execute.js',
        routePattern: 'buildFotMobMatchUrl(target.external_id)',
        sourceInventoryPattern: 'buildDetailRequestFromSourceInventoryPageUrl(',
    },
    {
        key: 'renewed_raw_write_execute',
        path: 'scripts/ops/renewed_pageprops_v2_raw_write_execute.js',
        routePattern: "require('./single_league_pageprops_v2_controlled_write_execute')",
        sourceInventoryPattern: 'buildDetailRequestFromSourceInventoryPageUrl(',
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

function hasText(text, pattern) {
    return normalizeText(text).includes(pattern);
}

function stripHash(rawUrl) {
    const value = normalizeText(rawUrl);
    if (!value) return null;
    return value.split('#')[0] || null;
}

function extractFragment(rawUrl) {
    const value = normalizeText(rawUrl);
    if (!value.includes('#')) return null;
    return value.slice(value.indexOf('#') + 1) || null;
}

function fragmentReachesServer(rawUrl) {
    return normalizeText(rawUrl).includes('#') ? false : false;
}

function summarizeManifestUrlFields(manifest = {}) {
    const targets = Array.isArray(manifest.candidate_targets) ? manifest.candidate_targets : [];
    const countWith = key => targets.filter(target => Boolean(normalizeText(target[key]))).length;
    return {
        candidate_targets_count: targets.length,
        external_id_count: countWith('external_id'),
        page_url_count: countWith('page_url'),
        pageUrl_count: countWith('pageUrl'),
        page_url_base_count: countWith('page_url_base'),
        source_inventory_page_url_base_count: countWith('source_inventory_page_url_base'),
        manifest_page_url_base_count: countWith('manifest_page_url_base'),
        source_inventory_record_key_count: countWith('source_inventory_record_key'),
        source_inventory_route_count: countWith('source_inventory_route'),
        source_url_count: countWith('source_url'),
    };
}

function analyzeSourceFiles(sourceFiles = SOURCE_FILES, dependencies = {}) {
    return sourceFiles.map(item => {
        const text =
            dependencies.sourceTextByPath?.[item.path] !== undefined
                ? dependencies.sourceTextByPath[item.path]
                : readTextFile(item.path);
        const usesMatchExternalIdRoute = hasText(text, item.routePattern);
        const usesSourceInventoryPageUrl = hasText(text, item.sourceInventoryPattern);
        const supportsRequestUrlOverride =
            item.key === 'fotmob_raw_detail_fetcher' && hasText(text, 'const requestUrl = v.requestUrl || request.url');
        return {
            key: item.key,
            path: item.path,
            route_pattern_found: usesMatchExternalIdRoute,
            uses_match_external_id_route: usesMatchExternalIdRoute,
            uses_source_inventory_page_url: usesSourceInventoryPageUrl,
            supports_request_url_override: supportsRequestUrlOverride,
        };
    });
}

function extractL2V3ESourceInventoryEvidence(reportText = '') {
    return {
        source_inventory_route_used: reportText.match(/source_inventory_route_used=([^\n]+)/)?.[1]?.trim() || null,
        source_inventory_request_url: reportText.match(/source_inventory_request_url=([^\n]+)/)?.[1]?.trim() || null,
        shared_page_url_base_pair_count: Number(reportText.match(/shared_page_url_base_pair_count=(\d+)/)?.[1] || 0),
        all_pairs_share_page_url_base: reportText.includes('all_pairs_share_page_url_base=true'),
        primary_evidence: reportText.match(/primary_evidence=([^\n]+)/)?.[1]?.trim() || null,
    };
}

function buildFetchPathSummary(sourceFileAnalysis = []) {
    const directOrDelegated = sourceFileAnalysis.filter(item => item.uses_match_external_id_route === true);
    const sourceInventoryUsers = sourceFileAnalysis.filter(item => item.uses_source_inventory_page_url === true);
    return {
        analyzed_fetch_paths_count: sourceFileAnalysis.length,
        current_url_strategy: 'fotmob_match_external_id_route',
        uses_match_external_id_route: directOrDelegated.length > 0,
        uses_source_inventory_page_url: sourceInventoryUsers.length > 0,
        fetch_paths_using_match_external_id_route_count: directOrDelegated.length,
        fetch_paths_using_source_inventory_page_url_count: sourceInventoryUsers.length,
        source_files: sourceFileAnalysis,
    };
}

function buildRouteCandidateAnalysis() {
    const sourceInventoryExample = 'https://www.fotmob.com/matches/marseille-vs-rennes/2t9n7h#4830466';
    return [
        {
            route_candidate: '/match/{externalId}',
            current_usage: true,
            preserves_schedule_external_id_in_url_path: true,
            uses_source_inventory_slug: false,
            fragment_preserved_in_request: false,
            fragment_reaches_server: false,
            risk: 'observed_schedule_id_can_resolve_to_reverse_fixture_or_slug_reuse_detail',
            recommendation: 'do_not_use_without_observed_detail_external_id_identity_guard',
        },
        {
            route_candidate: '/matches/{slug}#{externalId}',
            current_usage: false,
            example_url: sourceInventoryExample,
            page_url_base: stripHash(sourceInventoryExample),
            page_url_anchor: extractFragment(sourceInventoryExample),
            preserves_schedule_external_id_in_url_path: false,
            uses_source_inventory_slug: true,
            fragment_preserved_in_request: true,
            fragment_reaches_server: fragmentReachesServer(sourceInventoryExample),
            risk: 'hash_fragment_can_help_client_navigation_but_cannot_be_assumed_to_select_server_payload',
            recommendation: 'only_use_in_no_write_validation_with_explicit_observed_id_guard',
        },
        {
            route_candidate: '/api/data/matchDetails?matchId={externalId}',
            current_usage: false,
            preserves_schedule_external_id_in_url_path: true,
            uses_source_inventory_slug: false,
            fragment_preserved_in_request: false,
            fragment_reaches_server: false,
            risk: 'candidate_precise_endpoint_exists_in_codebase_but_current_live_feasibility_is_unknown_or_blocked',
            recommendation: 'requires_separate_no_write_api_endpoint_feasibility_verification_before_adoption',
        },
    ];
}

function validateInputs(manifest = {}, l2v3qArtifact = {}) {
    const errors = [];
    const nextRequiredStep = normalizeText(manifest.next_required_step);
    const alreadyCompleted =
        nextRequiredStep === NEXT_REQUIRED_STEP &&
        normalizeText(manifest.phase_5_21_l2v3r_planning_status) === ARTIFACT_STATUS;
    if (nextRequiredStep !== 'detail_url_construction_fix_planning' && !alreadyCompleted) {
        errors.push(
            'manifest next_required_step must be detail_url_construction_fix_planning or completed L2V3R output'
        );
    }
    if (manifest.raw_write_ready_for_execution !== false) {
        errors.push('manifest raw_write_ready_for_execution must remain false');
    }
    if (Number(l2v3qArtifact.detail_url_construction_suspect_count || 0) !== 42) {
        errors.push('L2V3Q detail_url_construction_suspect_count must be 42');
    }
    if (l2v3qArtifact.raw_write_ready_for_execution !== false) {
        errors.push('L2V3Q raw_write_ready_for_execution must remain false');
    }
    if (Number(l2v3qArtifact.accepted_mapping_count || 0) !== 0) {
        errors.push('L2V3Q accepted_mapping_count must remain 0');
    }
    return { ok: errors.length === 0, errors };
}

function buildArtifact({
    manifest,
    l2v3qArtifact,
    l2v3pArtifact,
    l2v3nArtifact,
    l2v3mArtifact,
    l2v3eReportText,
    sourceFileAnalysis,
    generatedAt = GENERATED_AT,
} = {}) {
    const manifestUrlFields = summarizeManifestUrlFields(manifest);
    const fetchPathSummary = buildFetchPathSummary(sourceFileAnalysis);
    const sourceInventoryEvidence = extractL2V3ESourceInventoryEvidence(l2v3eReportText);
    const routeCandidateAnalysis = buildRouteCandidateAnalysis();
    const detailUrlConstructionSuspectCount = Number(l2v3qArtifact.detail_url_construction_suspect_count || 0);
    const preciseDetailEndpointFound = 'unknown';
    const slugReuseRisk = detailUrlConstructionSuspectCount > 0;
    const proposedFixStrategy =
        'add_guarded_precise_detail_request_strategy_and_verify_api_match_details_feasibility_before_any_raw_write';

    return {
        artifact_type: 'detail_url_construction_fix_plan',
        artifact_status: ARTIFACT_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        source_phase: 'Phase 5.21L2V3Q',
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
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        accepted_mapping_count: 0,
        analyzed_fetch_paths_count: fetchPathSummary.analyzed_fetch_paths_count,
        current_url_strategy: fetchPathSummary.current_url_strategy,
        uses_match_external_id_route: fetchPathSummary.uses_match_external_id_route,
        uses_source_inventory_page_url: fetchPathSummary.uses_source_inventory_page_url,
        fragment_preserved_in_request: false,
        fragment_reaches_server: false,
        slug_reuse_risk: slugReuseRisk,
        precise_detail_endpoint_found: preciseDetailEndpointFound,
        detail_url_construction_suspect_count: detailUrlConstructionSuspectCount,
        proposed_fix_strategy: proposedFixStrategy,
        fix_confidence: 'medium',
        requires_followup_implementation: true,
        safety_contract: {
            detail_url_construction_plan_is_not_accepted_mapping: true,
            proposed_url_fix_is_not_raw_write_authorization: true,
            unresolved_url_construction_suspect_blocks_identity_mapping_acceptance: true,
            unresolved_url_construction_suspect_blocks_raw_write: true,
            slug_route_reuse_risk_blocks_raw_write: true,
            fragment_id_alone_is_not_identity_evidence: true,
            separate_identity_mapping_acceptance_required: true,
            separate_baseline_acceptance_required: true,
            separate_final_db_write_authorization_required: true,
        },
        source_artifacts: {
            proposal_manifest_path: MANIFEST_PATH,
            l2v3q_artifact_path: L2V3Q_ARTIFACT_PATH,
            l2v3q_report_path: L2V3Q_REPORT_PATH,
            l2v3p_artifact_path: L2V3P_ARTIFACT_PATH,
            l2v3n_artifact_path: L2V3N_ARTIFACT_PATH,
            l2v3m_artifact_path: L2V3M_ARTIFACT_PATH,
            l2v3e_report_path: L2V3E_REPORT_PATH,
        },
        upstream_counts: {
            l2v3q_analyzed_target_count: Number(l2v3qArtifact.analyzed_target_count || 0),
            l2v3q_unresolved_large_gap_count: Number(l2v3qArtifact.unresolved_large_gap_count || 0),
            l2v3q_likely_reverse_fixture_or_slug_reuse_count: Number(
                l2v3qArtifact.likely_reverse_fixture_or_slug_reuse_count || 0
            ),
            l2v3q_detail_url_construction_suspect_count: detailUrlConstructionSuspectCount,
            l2v3p_attempted_unknown_target_count: Number(l2v3pArtifact.attempted_unknown_target_count || 0),
            l2v3n_accepted_mapping_count: Number(l2v3nArtifact.accepted_mapping_count || 0),
            l2v3m_accepted_mapping_count: Number(l2v3mArtifact.accepted_mapping_count || 0),
        },
        manifest_url_field_summary: manifestUrlFields,
        source_inventory_evidence: sourceInventoryEvidence,
        fetch_path_summary: fetchPathSummary,
        route_candidate_analysis: routeCandidateAnalysis,
        planning_decisions: {
            use_match_external_id_route_without_guard: false,
            rely_on_url_fragment_for_server_identity: false,
            accept_identity_mapping_from_plan: false,
            accept_baseline_from_plan: false,
            authorize_raw_write_from_plan: false,
            required_identity_guard: 'observed_detail_external_id_must_equal_requested_schedule_external_id',
            no_write_validation_scope:
                '8 known reverse fixtures plus 42 L2V3Q unresolved_large_gap targets, metadata only, no full payload print/save',
            next_required_step: NEXT_REQUIRED_STEP,
            recommended_next_step: NEXT_RECOMMENDED_STEP,
        },
        recommended_next_step: NEXT_RECOMMENDED_STEP,
        next_required_step: NEXT_REQUIRED_STEP,
    };
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    return {
        ...manifest,
        phase_5_21_l2v3r_planning_status: artifact.artifact_status,
        detail_url_construction_fix_planning_status: artifact.artifact_status,
        phase_5_21_l2v3r_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3r_report_path: REPORT_PATH,
        analyzed_fetch_paths_count: artifact.analyzed_fetch_paths_count,
        phase_5_21_l2v3r_analyzed_fetch_paths_count: artifact.analyzed_fetch_paths_count,
        current_url_strategy: artifact.current_url_strategy,
        phase_5_21_l2v3r_current_url_strategy: artifact.current_url_strategy,
        uses_match_external_id_route: artifact.uses_match_external_id_route,
        phase_5_21_l2v3r_uses_match_external_id_route: artifact.uses_match_external_id_route,
        uses_source_inventory_page_url: artifact.uses_source_inventory_page_url,
        phase_5_21_l2v3r_uses_source_inventory_page_url: artifact.uses_source_inventory_page_url,
        slug_reuse_risk: artifact.slug_reuse_risk,
        phase_5_21_l2v3r_slug_reuse_risk: artifact.slug_reuse_risk,
        fragment_preserved_in_request: artifact.fragment_preserved_in_request,
        phase_5_21_l2v3r_fragment_preserved_in_request: artifact.fragment_preserved_in_request,
        fragment_reaches_server: artifact.fragment_reaches_server,
        phase_5_21_l2v3r_fragment_reaches_server: artifact.fragment_reaches_server,
        precise_detail_endpoint_found: artifact.precise_detail_endpoint_found,
        phase_5_21_l2v3r_precise_detail_endpoint_found: artifact.precise_detail_endpoint_found,
        detail_url_construction_suspect_count: artifact.detail_url_construction_suspect_count,
        phase_5_21_l2v3r_detail_url_construction_suspect_count: artifact.detail_url_construction_suspect_count,
        proposed_fix_strategy: artifact.proposed_fix_strategy,
        phase_5_21_l2v3r_proposed_fix_strategy: artifact.proposed_fix_strategy,
        fix_confidence: artifact.fix_confidence,
        phase_5_21_l2v3r_fix_confidence: artifact.fix_confidence,
        requires_followup_implementation: artifact.requires_followup_implementation,
        phase_5_21_l2v3r_requires_followup_implementation: artifact.requires_followup_implementation,
        accepted_mapping_count: 0,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        phase_5_21_l2v3r_accepted_mapping_count: 0,
        phase_5_21_l2v3r_identity_mapping_acceptance_performed: false,
        phase_5_21_l2v3r_baseline_acceptance_performed: false,
        phase_5_21_l2v3r_raw_write_retry_performed: false,
        phase_5_21_l2v3r_raw_write_ready_for_execution: false,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

function buildReport(artifact = {}) {
    return `# Data Entrypoint Governance - Phase 5.21 L2V3R

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- source_phase=Phase 5.21L2V3Q
- no_write=true
- live_source_check_performed=false
- network_request_performed=false
- db_write_performed=false
- raw_insert_performed=false
- matches_write_performed=false
- matches_external_id_modified=false
- schema_migration_performed=false
- parser_features_training_prediction_performed=false

## Safety Contract

- detail URL construction plan is not an accepted mapping.
- proposed URL fix is not raw write authorization.
- unresolved URL construction suspect blocks identity mapping acceptance and raw write.
- slug route reuse risk blocks raw write.
- URL fragment id alone is not accepted identity evidence.
- accepted_mapping_count=0.
- raw_write_ready_for_execution=false.
- separate identity mapping acceptance, baseline acceptance, and final DB-write authorization remain required.

## Current URL Strategy

- analyzed_fetch_paths_count=${artifact.analyzed_fetch_paths_count}
- current_url_strategy=${artifact.current_url_strategy}
- uses_match_external_id_route=${artifact.uses_match_external_id_route}
- uses_source_inventory_page_url=${artifact.uses_source_inventory_page_url}
- fragment_preserved_in_request=${artifact.fragment_preserved_in_request}
- fragment_reaches_server=${artifact.fragment_reaches_server}
- slug_reuse_risk=${artifact.slug_reuse_risk}
- precise_detail_endpoint_found=${artifact.precise_detail_endpoint_found}

## L2V3Q Evidence

- l2v3q_analyzed_target_count=${artifact.upstream_counts?.l2v3q_analyzed_target_count}
- unresolved_large_gap_count=${artifact.upstream_counts?.l2v3q_unresolved_large_gap_count}
- likely_reverse_fixture_or_slug_reuse_count=${artifact.upstream_counts?.l2v3q_likely_reverse_fixture_or_slug_reuse_count}
- detail_url_construction_suspect_count=${artifact.detail_url_construction_suspect_count}

## Source Inventory URL Fields

- manifest_candidate_targets_count=${artifact.manifest_url_field_summary?.candidate_targets_count}
- manifest_page_url_count=${artifact.manifest_url_field_summary?.page_url_count}
- manifest_page_url_base_count=${artifact.manifest_url_field_summary?.page_url_base_count}
- manifest_source_inventory_page_url_base_count=${artifact.manifest_url_field_summary?.source_inventory_page_url_base_count}
- l2v3e_shared_page_url_base_pair_count=${artifact.source_inventory_evidence?.shared_page_url_base_pair_count}
- l2v3e_all_pairs_share_page_url_base=${artifact.source_inventory_evidence?.all_pairs_share_page_url_base}

## Planning Conclusion

The current detail acquisition path constructs match detail requests with /match/{externalId}. The current candidate manifest does not preserve source inventory pageUrl, page_url_base, or fragment anchor fields. Earlier source-inventory reconciliation reported that requested and observed pairs can share a pageUrl base and differ only by a fragment anchor, but an HTTP request cannot rely on the fragment to select server-side payload identity. The plan therefore keeps all suspected URL construction cases blocked until a guarded precise-detail request strategy is implemented and validated in a separate no-write phase.

## Proposed Fix Strategy

- proposed_fix_strategy=${artifact.proposed_fix_strategy}
- fix_confidence=${artifact.fix_confidence}
- requires_followup_implementation=${artifact.requires_followup_implementation}
- required_identity_guard=${artifact.planning_decisions?.required_identity_guard}
- no_write_validation_scope=${artifact.planning_decisions?.no_write_validation_scope}

## Next Step

${artifact.recommended_next_step}
`;
}

function runDetailUrlConstructionFixPlan(dependencies = {}) {
    const manifest = dependencies.manifest || readJsonFile(MANIFEST_PATH);
    const l2v3qArtifact = dependencies.l2v3qArtifact || readJsonFile(L2V3Q_ARTIFACT_PATH);
    const l2v3pArtifact = dependencies.l2v3pArtifact || readJsonFile(L2V3P_ARTIFACT_PATH);
    const l2v3nArtifact = dependencies.l2v3nArtifact || readJsonFile(L2V3N_ARTIFACT_PATH);
    const l2v3mArtifact = dependencies.l2v3mArtifact || readJsonFile(L2V3M_ARTIFACT_PATH);
    const l2v3eReportText =
        dependencies.l2v3eReportText !== undefined ? dependencies.l2v3eReportText : readTextFile(L2V3E_REPORT_PATH);
    const inputGate = validateInputs(manifest, l2v3qArtifact);
    if (!inputGate.ok) return { ok: false, status: 2, errors: inputGate.errors };

    const sourceFileAnalysis = analyzeSourceFiles(SOURCE_FILES, dependencies);
    const artifact = buildArtifact({
        manifest,
        l2v3qArtifact,
        l2v3pArtifact,
        l2v3nArtifact,
        l2v3mArtifact,
        l2v3eReportText,
        sourceFileAnalysis,
        generatedAt: dependencies.generatedAt || GENERATED_AT,
    });
    const updatedManifest = updateManifestMetadata(manifest, artifact);
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

function runCli() {
    const result = runDetailUrlConstructionFixPlan();
    if (!result.ok) {
        process.stdout.write(`${JSON.stringify({ ok: false, phase: PHASE, errors: result.errors }, null, 2)}\n`);
        process.exitCode = result.status;
        return;
    }
    process.stdout.write(
        `${JSON.stringify(
            {
                ok: true,
                phase: PHASE,
                artifact: ARTIFACT_OUTPUT_PATH,
                report: REPORT_PATH,
                analyzed_fetch_paths_count: result.artifact.analyzed_fetch_paths_count,
                current_url_strategy: result.artifact.current_url_strategy,
                uses_match_external_id_route: result.artifact.uses_match_external_id_route,
                uses_source_inventory_page_url: result.artifact.uses_source_inventory_page_url,
                fragment_preserved_in_request: result.artifact.fragment_preserved_in_request,
                fragment_reaches_server: result.artifact.fragment_reaches_server,
                slug_reuse_risk: result.artifact.slug_reuse_risk,
                precise_detail_endpoint_found: result.artifact.precise_detail_endpoint_found,
                detail_url_construction_suspect_count: result.artifact.detail_url_construction_suspect_count,
                proposed_fix_strategy: result.artifact.proposed_fix_strategy,
                fix_confidence: result.artifact.fix_confidence,
                raw_write_ready_for_execution: result.artifact.raw_write_ready_for_execution,
                accepted_mapping_count: result.artifact.accepted_mapping_count,
                recommended_next_step: result.artifact.recommended_next_step,
            },
            null,
            2
        )}\n`
    );
    process.exitCode = result.status;
}

module.exports = {
    PHASE,
    PHASE_NAME,
    ARTIFACT_STATUS,
    MANIFEST_PATH,
    L2V3Q_ARTIFACT_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_PATH,
    NEXT_RECOMMENDED_STEP,
    NEXT_REQUIRED_STEP,
    stripHash,
    extractFragment,
    fragmentReachesServer,
    summarizeManifestUrlFields,
    analyzeSourceFiles,
    extractL2V3ESourceInventoryEvidence,
    buildFetchPathSummary,
    buildRouteCandidateAnalysis,
    validateInputs,
    buildArtifact,
    updateManifestMetadata,
    buildReport,
    runDetailUrlConstructionFixPlan,
};

if (require.main === module) {
    runCli();
}
