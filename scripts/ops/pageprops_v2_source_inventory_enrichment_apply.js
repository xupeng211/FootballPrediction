#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3V';
const PHASE_NAME = 'source_inventory_enrichment_implementation';
const ARTIFACT_STATUS = 'completed_no_write_source_inventory_enrichment_implementation';
const GENERATED_AT = '2026-05-21T09:00:00Z';
const MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const L2V3U_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.source_inventory_enrichment_plan.phase521l2v3u.json';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.source_inventory_enrichment_implementation.phase521l2v3v.json';
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3V.md';
const ENRICHMENT_STRATEGY = 'source_controlled_manifest_candidate_enrichment_from_source_inventory_pageUrl_metadata';
const NEXT_STEP_SOURCE_INVENTORY_DISCOVERY = 'Phase 5.21L2V3W: source inventory acquisition path investigation';
const NEXT_STEP_ENRICHED_VERIFICATION = 'Phase 5.21L2V3W: enriched no-write verification planning';
const NEXT_STEP_REGENERATION = 'Phase 5.21L2V3W: enriched target regeneration planning';

const ENRICHMENT_FIELDS = Object.freeze([
    'source_page_url',
    'source_page_url_base',
    'source_url_fragment_external_id',
    'source_slug',
    'source_route_code',
    'source_url_path_slug',
    'detail_external_id_candidate',
    'detail_identity_source',
    'schedule_external_id',
    'schedule_date',
    'schedule_home_team',
    'schedule_away_team',
    'source_inventory_record_key',
    'source_inventory_generated_at',
    'identity_evidence_status',
]);

const IMPLEMENTATION_PATHS = Object.freeze({
    source_inventory_adapter: 'src/infrastructure/services/FotMobSourceInventoryAdapter.js',
    source_inventory_preflight: 'scripts/ops/single_league_target_discovery_source_inventory_preflight.js',
    candidate_manifest_generation: 'scripts/ops/single_league_small_batch_target_manifest_plan.js',
});

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

function pickFirstText(values = []) {
    return values.map(normalizeText).find(Boolean) || null;
}

function parseSourcePageUrl(sourcePageUrl) {
    const value = normalizeText(sourcePageUrl);
    if (!value) {
        return {
            source_page_url_base: null,
            source_url_fragment_external_id: null,
            source_slug: null,
            source_route_code: null,
            source_url_path_slug: null,
        };
    }
    const hashIndex = value.indexOf('#');
    const base = hashIndex >= 0 ? value.slice(0, hashIndex) : value;
    let fragmentExternalId = null;
    let sourceSlug = null;
    let sourceRouteCode = null;

    try {
        const parsed = new URL(value, 'https://www.fotmob.com');
        const fragmentMatch = decodeURIComponent(parsed.hash || '').match(/\d+/);
        fragmentExternalId = fragmentMatch ? fragmentMatch[0] : null;
        const segments = parsed.pathname.split('/').filter(Boolean);
        const matchesIndex = segments.indexOf('matches');
        if (matchesIndex >= 0) {
            sourceSlug = segments[matchesIndex + 1] || null;
            sourceRouteCode = segments[matchesIndex + 2] || null;
        }
    } catch {
        fragmentExternalId = hashIndex >= 0 ? (value.slice(hashIndex + 1).match(/\d+/) || [null])[0] : null;
    }

    return {
        source_page_url_base: base || null,
        source_url_fragment_external_id: fragmentExternalId,
        source_slug: sourceSlug,
        source_route_code: sourceRouteCode,
        source_url_path_slug: sourceRouteCode,
    };
}

function buildDetailIdentityFields(sourceUrlFragmentExternalId) {
    const detailExternalIdCandidate = /^\d+$/.test(normalizeText(sourceUrlFragmentExternalId))
        ? normalizeText(sourceUrlFragmentExternalId)
        : null;
    return {
        detail_external_id_candidate: detailExternalIdCandidate,
        detail_identity_source: detailExternalIdCandidate ? 'url_hash_fragment' : null,
    };
}

function classifyIdentityEvidence(target = {}) {
    if (!normalizeText(target.source_page_url)) return 'missing';
    if (
        normalizeText(target.source_page_url_base) &&
        normalizeText(target.source_url_fragment_external_id) &&
        normalizeText(target.source_inventory_record_key) &&
        normalizeText(target.source_url_fragment_external_id) === normalizeText(target.external_id)
    ) {
        return 'complete';
    }
    return 'partial';
}

function enrichCandidateTarget(target = {}) {
    const sourcePageUrl = pickFirstText([
        target.source_page_url,
        target.pageUrl,
        target.page_url,
        target.matchUrl,
        target.match_url,
        target.href,
        target.source_url,
    ]);
    const parsed = parseSourcePageUrl(sourcePageUrl);
    const enriched = {
        ...target,
        source_page_url: sourcePageUrl,
        source_page_url_base: pickFirstText([
            target.source_page_url_base,
            target.page_url_base,
            parsed.source_page_url_base,
        ]),
        source_url_fragment_external_id: pickFirstText([
            target.source_url_fragment_external_id,
            target.source_page_url_fragment_external_id,
            parsed.source_url_fragment_external_id,
        ]),
        source_slug: pickFirstText([target.source_slug, parsed.source_slug]),
        source_route_code: pickFirstText([target.source_route_code, parsed.source_route_code]),
        source_url_path_slug: pickFirstText([
            target.source_url_path_slug,
            target.source_route_code,
            parsed.source_url_path_slug,
            parsed.source_route_code,
        ]),
        schedule_external_id: pickFirstText([target.schedule_external_id, target.external_id]),
        schedule_date: pickFirstText([target.schedule_date, target.match_date, target.kickoff_time]),
        schedule_home_team: pickFirstText([target.schedule_home_team, target.home_team]),
        schedule_away_team: pickFirstText([target.schedule_away_team, target.away_team]),
        source_inventory_record_key: pickFirstText([target.source_inventory_record_key]),
        source_inventory_generated_at: pickFirstText([target.source_inventory_generated_at]) || 'unknown',
    };
    const detailIdentity = buildDetailIdentityFields(enriched.source_url_fragment_external_id);
    return {
        ...enriched,
        detail_external_id_candidate: pickFirstText([
            target.detail_external_id_candidate,
            detailIdentity.detail_external_id_candidate,
        ]),
        detail_identity_source: pickFirstText([target.detail_identity_source, detailIdentity.detail_identity_source]),
        identity_evidence_status: target.identity_evidence_status || classifyIdentityEvidence(enriched),
    };
}

function ensureSchemaFields(schema = []) {
    const current = Array.isArray(schema) ? [...schema] : [];
    const existingFields = new Set(current.map(item => item?.field).filter(Boolean));
    for (const field of ENRICHMENT_FIELDS) {
        if (!existingFields.has(field)) {
            current.push({ field, required_for_future_target: true });
        }
    }
    return current;
}

function buildCandidateSummary(candidateTargets = []) {
    const checked = candidateTargets.length;
    const statusDistribution = candidateTargets.reduce((acc, target) => {
        const status = normalizeText(target.identity_evidence_status) || 'unknown';
        acc[status] = (acc[status] || 0) + 1;
        return acc;
    }, {});
    return {
        candidate_targets_checked: checked,
        candidate_targets_with_source_page_url: candidateTargets.filter(target => normalizeText(target.source_page_url))
            .length,
        candidate_targets_with_source_page_url_base: candidateTargets.filter(target =>
            normalizeText(target.source_page_url_base)
        ).length,
        candidate_targets_with_source_url_fragment_external_id: candidateTargets.filter(target =>
            normalizeText(target.source_url_fragment_external_id)
        ).length,
        candidate_targets_with_source_inventory_record_key: candidateTargets.filter(target =>
            normalizeText(target.source_inventory_record_key)
        ).length,
        identity_evidence_complete_count: statusDistribution.complete || 0,
        identity_evidence_partial_count: statusDistribution.partial || 0,
        identity_evidence_missing_count: statusDistribution.missing || 0,
        identity_evidence_unknown_count: statusDistribution.unknown || 0,
        identity_evidence_status_distribution: statusDistribution,
        raw_write_blocked_count: checked,
    };
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

function buildImplementationCoverage(dependencies = {}) {
    const adapterText = readImplementationText(IMPLEMENTATION_PATHS.source_inventory_adapter, dependencies);
    const preflightText = readImplementationText(IMPLEMENTATION_PATHS.source_inventory_preflight, dependencies);
    const manifestBuilderText = readImplementationText(
        IMPLEMENTATION_PATHS.candidate_manifest_generation,
        dependencies
    );

    return {
        source_inventory_adapter_updated:
            adapterText.includes('deriveSourceInventoryIdentityEvidence') &&
            adapterText.includes('source_page_url_base') &&
            adapterText.includes('source_url_fragment_external_id'),
        manifest_candidate_builder_updated:
            preflightText.includes('source_inventory_record_key') &&
            preflightText.includes('identity_evidence_status') &&
            manifestBuilderText.includes('source_inventory_record_key') &&
            manifestBuilderText.includes('identity_evidence_status'),
        implementation_paths_checked: Object.values(IMPLEMENTATION_PATHS),
    };
}

function recommendedNextStep(summary = {}) {
    if (summary.candidate_targets_checked !== 50) {
        return {
            recommended_next_step: 'Phase 5.21L2V3W: continued source inventory enrichment implementation',
            next_required_step: 'continued_source_inventory_enrichment_implementation',
        };
    }
    if (
        summary.candidate_targets_with_source_page_url === 0 ||
        summary.candidate_targets_with_source_page_url_base === 0 ||
        summary.candidate_targets_with_source_url_fragment_external_id === 0
    ) {
        return {
            recommended_next_step: NEXT_STEP_SOURCE_INVENTORY_DISCOVERY,
            next_required_step: 'source_inventory_acquisition_path_investigation',
        };
    }
    if (summary.identity_evidence_complete_count === summary.candidate_targets_checked) {
        return {
            recommended_next_step: NEXT_STEP_ENRICHED_VERIFICATION,
            next_required_step: 'enriched_no_write_verification_planning',
        };
    }
    return {
        recommended_next_step: NEXT_STEP_REGENERATION,
        next_required_step: 'enriched_target_regeneration_planning',
    };
}

function validateInputs(manifest = {}, l2v3uArtifact = {}) {
    const errors = [];
    const alreadyCompleted =
        normalizeText(manifest.phase_5_21_l2v3v_implementation_status) === ARTIFACT_STATUS &&
        normalizeText(manifest.source_inventory_enrichment_implementation_status) === ARTIFACT_STATUS;
    if (
        normalizeText(manifest.next_required_step) !== 'source_inventory_enrichment_implementation' &&
        !alreadyCompleted
    ) {
        errors.push('manifest next_required_step must be source_inventory_enrichment_implementation');
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
    if (normalizeText(l2v3uArtifact.proposal_phase) !== 'Phase 5.21L2V3U') {
        errors.push('L2V3U artifact must be present');
    }
    if (l2v3uArtifact.raw_write_ready_for_execution !== false) {
        errors.push('L2V3U raw_write_ready_for_execution must remain false');
    }
    if (Number(l2v3uArtifact.accepted_mapping_count || 0) !== 0) {
        errors.push('L2V3U accepted_mapping_count must remain 0');
    }
    if (l2v3uArtifact.requires_followup_implementation !== true) {
        errors.push('L2V3U requires_followup_implementation must be true');
    }
    if (normalizeText(l2v3uArtifact.next_required_step) !== 'source_inventory_enrichment_implementation') {
        errors.push('L2V3U next_required_step must be source_inventory_enrichment_implementation');
    }
    return { ok: errors.length === 0, errors };
}

function buildArtifact({
    manifest = {},
    enrichedTargets = [],
    l2v3uArtifact = {},
    generatedAt = GENERATED_AT,
    dependencies = {},
} = {}) {
    const summary = buildCandidateSummary(enrichedTargets);
    const coverage = buildImplementationCoverage(dependencies);
    const next = recommendedNextStep(summary);

    return {
        artifact_type: 'source_inventory_enrichment_implementation',
        artifact_status: ARTIFACT_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        source_phase: 'Phase 5.21L2V3U',
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
        raw_write_ready_for_execution: false,
        accepted_mapping_count: 0,
        implemented_enrichment_field_count: ENRICHMENT_FIELDS.length,
        source_inventory_adapter_updated: coverage.source_inventory_adapter_updated,
        manifest_candidate_builder_updated: coverage.manifest_candidate_builder_updated,
        candidate_targets_checked: summary.candidate_targets_checked,
        candidate_targets_with_source_page_url: summary.candidate_targets_with_source_page_url,
        candidate_targets_with_source_page_url_base: summary.candidate_targets_with_source_page_url_base,
        candidate_targets_with_source_url_fragment_external_id:
            summary.candidate_targets_with_source_url_fragment_external_id,
        candidate_targets_with_source_inventory_record_key: summary.candidate_targets_with_source_inventory_record_key,
        identity_evidence_complete_count: summary.identity_evidence_complete_count,
        identity_evidence_partial_count: summary.identity_evidence_partial_count,
        identity_evidence_missing_count: summary.identity_evidence_missing_count,
        identity_evidence_unknown_count: summary.identity_evidence_unknown_count,
        raw_write_blocked_count: summary.raw_write_blocked_count,
        enrichment_strategy: ENRICHMENT_STRATEGY,
        enrichment_confidence: l2v3uArtifact.enrichment_confidence || 'medium',
        current_manifest_candidate_count: Array.isArray(manifest.candidate_targets)
            ? manifest.candidate_targets.length
            : 0,
        implemented_fields: ENRICHMENT_FIELDS.map(field => ({
            field,
            generated_from_source_controlled_metadata_only: true,
            unblocks_raw_write: false,
            implies_accepted_mapping: false,
        })),
        implementation_coverage: coverage,
        safety_contract: {
            enriched_source_inventory_result_is_not_accepted_mapping: true,
            enriched_source_inventory_result_is_not_raw_write_authorization: true,
            enriched_source_inventory_result_is_not_baseline_acceptance: true,
            enriched_source_inventory_result_is_not_raw_write_retry: true,
            source_url_fragment_external_id_match_does_not_imply_accepted_mapping: true,
            source_page_url_base_match_does_not_imply_raw_write_ready_for_execution: true,
            missing_page_url_remains_blocker_until_regenerated_and_reviewed: true,
            separate_identity_mapping_acceptance_required: true,
            separate_baseline_acceptance_required: true,
            separate_final_db_write_authorization_required: true,
        },
        upstream_l2v3u_summary: {
            analyzed_inventory_path_count: l2v3uArtifact.analyzed_inventory_path_count ?? null,
            missing_source_page_url_count: l2v3uArtifact.missing_source_page_url_count ?? null,
            missing_page_url_base_count: l2v3uArtifact.missing_page_url_base_count ?? null,
            missing_url_fragment_external_id_count: l2v3uArtifact.missing_url_fragment_external_id_count ?? null,
            missing_source_record_key_count: l2v3uArtifact.missing_source_record_key_count ?? null,
            requires_followup_implementation: l2v3uArtifact.requires_followup_implementation ?? null,
            requires_target_regeneration: l2v3uArtifact.requires_target_regeneration ?? null,
        },
        recommended_next_step: next.recommended_next_step,
        next_required_step: next.next_required_step,
    };
}

function updateManifestMetadata(manifest = {}, enrichedTargets = [], artifact = {}) {
    return {
        ...manifest,
        candidate_targets: enrichedTargets,
        target_manifest_schema: ensureSchemaFields(manifest.target_manifest_schema),
        phase_5_21_l2v3v_implementation_status: artifact.artifact_status,
        source_inventory_enrichment_implementation_status: artifact.artifact_status,
        phase_5_21_l2v3v_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3v_report_path: REPORT_PATH,
        implemented_enrichment_field_count: artifact.implemented_enrichment_field_count,
        phase_5_21_l2v3v_implemented_enrichment_field_count: artifact.implemented_enrichment_field_count,
        source_inventory_adapter_updated: artifact.source_inventory_adapter_updated,
        manifest_candidate_builder_updated: artifact.manifest_candidate_builder_updated,
        candidate_targets_checked: artifact.candidate_targets_checked,
        phase_5_21_l2v3v_candidate_targets_checked: artifact.candidate_targets_checked,
        candidate_targets_with_source_page_url: artifact.candidate_targets_with_source_page_url,
        candidate_targets_with_source_page_url_base: artifact.candidate_targets_with_source_page_url_base,
        candidate_targets_with_source_url_fragment_external_id:
            artifact.candidate_targets_with_source_url_fragment_external_id,
        candidate_targets_with_source_inventory_record_key: artifact.candidate_targets_with_source_inventory_record_key,
        identity_evidence_complete_count: artifact.identity_evidence_complete_count,
        identity_evidence_partial_count: artifact.identity_evidence_partial_count,
        identity_evidence_missing_count: artifact.identity_evidence_missing_count,
        raw_write_blocked_count: artifact.raw_write_blocked_count,
        phase_5_21_l2v3v_identity_evidence_complete_count: artifact.identity_evidence_complete_count,
        phase_5_21_l2v3v_identity_evidence_partial_count: artifact.identity_evidence_partial_count,
        phase_5_21_l2v3v_identity_evidence_missing_count: artifact.identity_evidence_missing_count,
        phase_5_21_l2v3v_raw_write_blocked_count: artifact.raw_write_blocked_count,
        phase_5_21_l2v3v_enrichment_strategy: artifact.enrichment_strategy,
        phase_5_21_l2v3v_enrichment_confidence: artifact.enrichment_confidence,
        accepted_mapping_count: 0,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        phase_5_21_l2v3v_accepted_mapping_count: 0,
        phase_5_21_l2v3v_identity_mapping_acceptance_performed: false,
        phase_5_21_l2v3v_baseline_acceptance_performed: false,
        phase_5_21_l2v3v_raw_write_retry_performed: false,
        phase_5_21_l2v3v_raw_write_ready_for_execution: false,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

function buildReport(artifact = {}) {
    return `# Data Entrypoint Governance - Phase 5.21 L2V3V

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

- implemented_enrichment_field_count=${artifact.implemented_enrichment_field_count}
- source_inventory_adapter_updated=${artifact.source_inventory_adapter_updated}
- manifest_candidate_builder_updated=${artifact.manifest_candidate_builder_updated}
- candidate_targets_checked=${artifact.candidate_targets_checked}
- candidate_targets_with_source_page_url=${artifact.candidate_targets_with_source_page_url}
- candidate_targets_with_source_page_url_base=${artifact.candidate_targets_with_source_page_url_base}
- candidate_targets_with_source_url_fragment_external_id=${artifact.candidate_targets_with_source_url_fragment_external_id}
- candidate_targets_with_source_inventory_record_key=${artifact.candidate_targets_with_source_inventory_record_key}
- identity_evidence_complete_count=${artifact.identity_evidence_complete_count}
- identity_evidence_partial_count=${artifact.identity_evidence_partial_count}
- identity_evidence_missing_count=${artifact.identity_evidence_missing_count}
- raw_write_blocked_count=${artifact.raw_write_blocked_count}
- accepted_mapping_count=0
- raw_write_ready_for_execution=false

## Enriched Fields

${artifact.implemented_fields.map(item => `- ${item.field}: source-controlled metadata only; no accepted mapping; no raw write authorization`).join('\n')}

## Current 50 Candidate Result

The current source-controlled manifest now carries the enrichment schema, but the 50 existing candidate targets still do not have source_page_url, source_page_url_base, source_url_fragment_external_id, or source_inventory_record_key evidence from a source-controlled inventory record. These missing requested-side URL fields remain blockers and require a later source inventory acquisition path investigation or regeneration/review step.

## Safety Contract

- enriched source inventory result is not accepted mapping.
- enriched source inventory result is not raw write authorization.
- enriched source inventory result is not baseline acceptance.
- enriched source inventory result is not raw write retry.
- source_url_fragment_external_id match does not imply accepted mapping.
- source_page_url_base match does not imply raw_write_ready_for_execution.
- missing pageUrl remains blocked until regenerated and reviewed.
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
        l2v3uArtifact: dependencies.l2v3uArtifact || readJsonFile(L2V3U_ARTIFACT_PATH),
    };
}

function runSourceInventoryEnrichmentApply(dependencies = {}) {
    const loaded = loadDependencies(dependencies);
    const inputGate = validateInputs(loaded.manifest, loaded.l2v3uArtifact);
    if (!inputGate.ok) return { ok: false, status: 3, errors: inputGate.errors };

    const enrichedTargets = loaded.manifest.candidate_targets.map(enrichCandidateTarget);
    const artifact = buildArtifact({
        manifest: loaded.manifest,
        enrichedTargets,
        l2v3uArtifact: loaded.l2v3uArtifact,
        generatedAt: dependencies.generatedAt || GENERATED_AT,
        dependencies,
    });
    const updatedManifest = updateManifestMetadata(loaded.manifest, enrichedTargets, artifact);
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
        '  node scripts/ops/pageprops_v2_source_inventory_enrichment_apply.js --write-files=yes',
        '',
        'Safety:',
        '  L2V3V is a no-write source inventory enrichment implementation phase.',
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
    const result = runSourceInventoryEnrichmentApply({ writeFiles: options.writeFiles });
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
                implemented_enrichment_field_count: result.artifact.implemented_enrichment_field_count,
                source_inventory_adapter_updated: result.artifact.source_inventory_adapter_updated,
                manifest_candidate_builder_updated: result.artifact.manifest_candidate_builder_updated,
                candidate_targets_checked: result.artifact.candidate_targets_checked,
                candidate_targets_with_source_page_url: result.artifact.candidate_targets_with_source_page_url,
                candidate_targets_with_source_page_url_base:
                    result.artifact.candidate_targets_with_source_page_url_base,
                candidate_targets_with_source_url_fragment_external_id:
                    result.artifact.candidate_targets_with_source_url_fragment_external_id,
                candidate_targets_with_source_inventory_record_key:
                    result.artifact.candidate_targets_with_source_inventory_record_key,
                identity_evidence_complete_count: result.artifact.identity_evidence_complete_count,
                identity_evidence_partial_count: result.artifact.identity_evidence_partial_count,
                identity_evidence_missing_count: result.artifact.identity_evidence_missing_count,
                raw_write_blocked_count: result.artifact.raw_write_blocked_count,
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
    L2V3U_ARTIFACT_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_PATH,
    ENRICHMENT_FIELDS,
    IMPLEMENTATION_PATHS,
    parseArgs,
    validateCliOptions,
    parseSourcePageUrl,
    enrichCandidateTarget,
    ensureSchemaFields,
    buildCandidateSummary,
    buildImplementationCoverage,
    recommendedNextStep,
    validateInputs,
    buildArtifact,
    updateManifestMetadata,
    buildReport,
    runSourceInventoryEnrichmentApply,
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
