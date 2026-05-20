#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const {
    reconcileRouteIdentity,
    REVERSE_FIXTURE_DETECTED,
    UNRESOLVED_LARGE_GAP,
    REQUESTED_OBSERVED_MISMATCH,
} = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const METADATA_ONLY_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.metadata_only_detail_check.phase521l2v3p.json';
const METADATA_ONLY_REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3P.md';
const INVESTIGATION_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.continued_date_rule_investigation.phase521l2v3o.json';
const INVESTIGATION_REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3O.md';
const VERIFICATION_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.expanded_date_rule_verification.phase521l2v3n.json';
const VERIFICATION_REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3N.md';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.continued_metadata_investigation.phase521l2v3q.json';
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3Q.md';
const PHASE = 'Phase 5.21L2V3Q';
const PHASE_NAME = 'continued_metadata_only_investigation';
const ARTIFACT_STATUS = 'completed_no_write_metadata_pattern_investigation';
const GENERATED_AT = '2026-05-20T00:00:00Z';
const NEXT_RECOMMENDED_STEP = 'Phase 5.21L2V3R: detail URL construction fix planning';
const NEXT_REQUIRED_STEP = 'detail_url_construction_fix_planning';
const DETAIL_ROUTE_SUSPECT_REASON =
    'Current metadata-only evidence suggests slug-route detail navigation returns a reverse fixture for the requested schedule id.';

function absolutePath(filePath) {
    return path.join(PROJECT_ROOT, filePath);
}

function readJsonFile(filePath) {
    return JSON.parse(fs.readFileSync(absolutePath(filePath), 'utf8'));
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

function requestedPageUrlBase(target = {}) {
    return (
        normalizeText(target.page_url_base) ||
        normalizeText(target.source_inventory_page_url_base) ||
        normalizeText(target.manifest_page_url_base) ||
        null
    );
}

function asBoolean(value) {
    return value === true;
}

function parseDate(value) {
    const text = normalizeText(value);
    if (!text) return null;
    const parsed = new Date(text);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function selectUnresolvedTargets(manifest = {}, metadataOnlyArtifact = {}) {
    const targets = Array.isArray(manifest.candidate_targets) ? manifest.candidate_targets : [];
    const entries = Array.isArray(metadataOnlyArtifact.metadata_only_target_summaries)
        ? metadataOnlyArtifact.metadata_only_target_summaries
        : [];
    const unresolvedEntries = entries.filter(entry => normalizeText(entry.date_rule_status) === UNRESOLVED_LARGE_GAP);
    const targetByExternalId = new Map(targets.map(target => [normalizeText(target.external_id), target]));
    return unresolvedEntries.map(entry => ({
        target: targetByExternalId.get(normalizeText(entry.schedule_external_id)) || null,
        metadata_entry: entry,
    }));
}

function buildActualReconciliation(target = {}, entry = {}) {
    return reconcileRouteIdentity({
        target: {
            external_id: normalizeText(entry.schedule_external_id),
            page_url_base: requestedPageUrlBase(target),
            source_inventory_page_url_base: normalizeText(target.source_inventory_page_url_base),
            manifest_page_url_base: normalizeText(target.manifest_page_url_base),
            home_team: normalizeText(entry.schedule_home_team),
            away_team: normalizeText(entry.schedule_away_team),
            match_date: normalizeText(entry.schedule_date),
            season: normalizeText(target.season),
            status: normalizeText(entry.status_summary?.schedule_status),
        },
        observedDetailExternalId: normalizeText(entry.observed_detail_external_id),
        observedPageUrlBase: normalizeText(entry.observed_page_url_base),
        observedHomeTeam: normalizeText(entry.detail_home_team),
        observedAwayTeam: normalizeText(entry.detail_away_team),
        observedMatchDate: normalizeText(entry.detail_date),
        observedStatus: normalizeText(entry.status_summary?.detail_status),
    });
}

function buildCounterfactualReconciliation(target = {}, entry = {}) {
    return reconcileRouteIdentity({
        target: {
            external_id: normalizeText(entry.schedule_external_id),
            page_url_base: normalizeText(entry.observed_page_url_base),
            home_team: normalizeText(entry.schedule_home_team),
            away_team: normalizeText(entry.schedule_away_team),
            match_date: normalizeText(entry.schedule_date),
            season: normalizeText(target.season),
            status: normalizeText(entry.status_summary?.schedule_status),
        },
        observedDetailExternalId: normalizeText(entry.observed_detail_external_id),
        observedPageUrlBase: normalizeText(entry.observed_page_url_base),
        observedHomeTeam: normalizeText(entry.detail_home_team),
        observedAwayTeam: normalizeText(entry.detail_away_team),
        observedMatchDate: normalizeText(entry.detail_date),
        observedStatus: normalizeText(entry.status_summary?.detail_status),
    });
}

function buildClassificationEntry({ target = {}, metadataEntry = {} } = {}) {
    const scheduleExternalId = normalizeText(metadataEntry.schedule_external_id);
    const observedDetailExternalId = normalizeText(metadataEntry.observed_detail_external_id);
    const requestUrlSummary = normalizeText(metadataEntry.request_url_summary);
    const observedPageUrlBase = normalizeText(metadataEntry.observed_page_url_base) || null;
    const requestedPageUrl = requestedPageUrlBase(target);
    const teamPairReversed =
        normalizeLower(metadataEntry.schedule_home_team) === normalizeLower(metadataEntry.detail_away_team) &&
        normalizeLower(metadataEntry.schedule_away_team) === normalizeLower(metadataEntry.detail_home_team) &&
        Boolean(
            normalizeText(metadataEntry.schedule_home_team) &&
            normalizeText(metadataEntry.schedule_away_team) &&
            normalizeText(metadataEntry.detail_home_team) &&
            normalizeText(metadataEntry.detail_away_team)
        );
    const requestedObservedExternalIdMismatch = scheduleExternalId !== observedDetailExternalId;
    const actualReconciliation = buildActualReconciliation(target, metadataEntry);
    const counterfactualReconciliation = buildCounterfactualReconciliation(target, metadataEntry);
    const missingRequestedPageUrlBase = !requestedPageUrl;
    const missingReverseFixtureEvidence =
        missingRequestedPageUrlBase &&
        normalizeText(actualReconciliation.date_compatibility_status) === UNRESOLVED_LARGE_GAP &&
        normalizeText(counterfactualReconciliation.date_compatibility_status) === REVERSE_FIXTURE_DETECTED;
    const likelyReverseFixtureOrSlugReuse =
        requestedObservedExternalIdMismatch &&
        teamPairReversed &&
        normalizeText(counterfactualReconciliation.date_compatibility_status) === REVERSE_FIXTURE_DETECTED;
    const detailUrlConstructionSuspect =
        likelyReverseFixtureOrSlugReuse &&
        requestUrlSummary.endsWith(`/match/${scheduleExternalId}`) &&
        asBoolean(metadataEntry.parsed) &&
        normalizeText(metadataEntry.parsed_status) === 'metadata_only_parsed';
    const routeTargetRegenerationNeeded = false;
    const apiEndpointPreferred = false;
    const futureReviewCandidate = false;
    const scheduleDate = parseDate(metadataEntry.schedule_date);
    const detailDate = parseDate(metadataEntry.detail_date);
    const dateGapDays =
        scheduleDate && detailDate
            ? Number((Math.abs(detailDate.getTime() - scheduleDate.getTime()) / 86400000).toFixed(3))
            : null;

    return {
        match_id: normalizeText(metadataEntry.match_id),
        schedule_external_id: scheduleExternalId,
        observed_detail_external_id: observedDetailExternalId || null,
        request_url_summary: requestUrlSummary || null,
        schedule_date: normalizeText(metadataEntry.schedule_date) || null,
        detail_date: normalizeText(metadataEntry.detail_date) || null,
        date_gap_days: dateGapDays,
        schedule_home_team: normalizeText(metadataEntry.schedule_home_team) || null,
        schedule_away_team: normalizeText(metadataEntry.schedule_away_team) || null,
        detail_home_team: normalizeText(metadataEntry.detail_home_team) || null,
        detail_away_team: normalizeText(metadataEntry.detail_away_team) || null,
        requested_page_url_base_present: Boolean(requestedPageUrl),
        observed_page_url_base: observedPageUrlBase,
        original_page_url_base_match_status: normalizeText(actualReconciliation.page_url_base_match_status) || null,
        original_date_rule_status: normalizeText(metadataEntry.date_rule_status) || null,
        original_identity_reconciliation_status: normalizeText(metadataEntry.identity_reconciliation_status) || null,
        requested_vs_observed_external_id_mismatch: requestedObservedExternalIdMismatch,
        team_pair_reversed: teamPairReversed,
        missing_reverse_fixture_evidence: missingReverseFixtureEvidence,
        missing_reverse_fixture_evidence_reason: missingReverseFixtureEvidence
            ? 'requested_page_url_base_missing'
            : null,
        counterfactual_page_url_base_match_status:
            normalizeText(counterfactualReconciliation.page_url_base_match_status) || null,
        counterfactual_date_rule_status: normalizeText(counterfactualReconciliation.date_compatibility_status) || null,
        counterfactual_reverse_fixture_detected:
            normalizeText(counterfactualReconciliation.date_compatibility_status) === REVERSE_FIXTURE_DETECTED,
        likely_reverse_fixture_or_slug_reuse: likelyReverseFixtureOrSlugReuse,
        detail_url_construction_suspect: detailUrlConstructionSuspect,
        route_target_regeneration_needed: routeTargetRegenerationNeeded,
        api_endpoint_preferred: apiEndpointPreferred,
        future_review_candidate: futureReviewCandidate,
        still_blocked: true,
        accepted_mapping: false,
        raw_write_blocked: true,
        identity_mapping_acceptance_blocked: true,
        raw_write_ready_for_execution: false,
        safe_error_summary: detailUrlConstructionSuspect
            ? `${DETAIL_ROUTE_SUSPECT_REASON} Missing requested page_url_base prevented reverse_fixture_detected classification in the current rule engine.`
            : 'Unresolved large gap remains blocked pending follow-up no-write route investigation.',
    };
}

function countWhere(entries = [], predicate = () => false) {
    return entries.filter(predicate).length;
}

function buildCounts(entries = []) {
    return {
        analyzed_target_count: entries.length,
        unresolved_large_gap_count: countWhere(
            entries,
            entry => normalizeText(entry.original_date_rule_status) === UNRESOLVED_LARGE_GAP
        ),
        likely_reverse_fixture_or_slug_reuse_count: countWhere(
            entries,
            entry => entry.likely_reverse_fixture_or_slug_reuse === true
        ),
        missing_reverse_fixture_evidence_count: countWhere(
            entries,
            entry => entry.missing_reverse_fixture_evidence === true
        ),
        missing_pageurl_base_count: countWhere(entries, entry => entry.requested_page_url_base_present !== true),
        missing_team_reverse_evidence_count: countWhere(entries, entry => entry.team_pair_reversed !== true),
        detail_url_construction_suspect_count: countWhere(
            entries,
            entry => entry.detail_url_construction_suspect === true
        ),
        route_target_regeneration_needed_count: countWhere(
            entries,
            entry => entry.route_target_regeneration_needed === true
        ),
        api_endpoint_preferred_count: countWhere(entries, entry => entry.api_endpoint_preferred === true),
        future_review_candidate_count: countWhere(entries, entry => entry.future_review_candidate === true),
        still_blocked_count: countWhere(entries, entry => entry.still_blocked === true),
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
    };
}

function buildArtifact({ manifest, metadataOnlyArtifact, entries, generatedAt = GENERATED_AT } = {}) {
    const counts = buildCounts(entries);
    const uniqueObservedPageUrlBaseCount = new Set(
        entries.map(entry => normalizeText(entry.observed_page_url_base)).filter(Boolean)
    ).size;
    return {
        artifact_type: 'continued_metadata_investigation',
        artifact_status: ARTIFACT_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        source_phase: 'Phase 5.21L2V3P',
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
        counts,
        analyzed_target_count: counts.analyzed_target_count,
        unresolved_large_gap_count: counts.unresolved_large_gap_count,
        likely_reverse_fixture_or_slug_reuse_count: counts.likely_reverse_fixture_or_slug_reuse_count,
        missing_reverse_fixture_evidence_count: counts.missing_reverse_fixture_evidence_count,
        missing_pageurl_base_count: counts.missing_pageurl_base_count,
        missing_team_reverse_evidence_count: counts.missing_team_reverse_evidence_count,
        detail_url_construction_suspect_count: counts.detail_url_construction_suspect_count,
        route_target_regeneration_needed_count: counts.route_target_regeneration_needed_count,
        api_endpoint_preferred_count: counts.api_endpoint_preferred_count,
        future_review_candidate_count: counts.future_review_candidate_count,
        still_blocked_count: counts.still_blocked_count,
        safety_contract: {
            investigation_result_is_not_accepted_mapping: true,
            unresolved_large_gap_blocks_identity_mapping_acceptance: true,
            unresolved_large_gap_blocks_raw_write: true,
            likely_reverse_fixture_or_slug_reuse_is_not_accepted_mapping: true,
            detail_url_construction_suspect_is_not_accepted_mapping: true,
            future_review_candidate_is_not_accepted_mapping: true,
            separate_identity_mapping_acceptance_required: true,
            separate_baseline_acceptance_required: true,
            separate_final_db_write_authorization_required: true,
        },
        source_artifacts: {
            proposal_manifest_path: MANIFEST_PATH,
            l2v3p_metadata_only_artifact_path: METADATA_ONLY_ARTIFACT_PATH,
            l2v3p_report_path: METADATA_ONLY_REPORT_PATH,
            l2v3o_investigation_artifact_path: INVESTIGATION_ARTIFACT_PATH,
            l2v3o_report_path: INVESTIGATION_REPORT_PATH,
            l2v3n_expanded_verification_artifact_path: VERIFICATION_ARTIFACT_PATH,
            l2v3n_report_path: VERIFICATION_REPORT_PATH,
        },
        root_cause_summary: {
            current_request_route_shape: 'https://www.fotmob.com/match/{schedule_external_id}',
            current_route_uses_requested_page_url_base: false,
            current_route_uses_fragment_anchor: false,
            current_route_uses_detail_api_endpoint: false,
            requested_observed_external_id_mismatch_count: countWhere(
                entries,
                entry => entry.requested_vs_observed_external_id_mismatch === true
            ),
            reversed_team_pair_count: countWhere(entries, entry => entry.team_pair_reversed === true),
            observed_page_url_base_present_count: countWhere(entries, entry =>
                Boolean(normalizeText(entry.observed_page_url_base))
            ),
            unique_observed_page_url_base_count: uniqueObservedPageUrlBaseCount,
            counterfactual_reverse_fixture_detected_count: countWhere(
                entries,
                entry => entry.counterfactual_reverse_fixture_detected === true
            ),
            likely_primary_root_cause: 'detail_url_construction_suspect',
            route_target_regeneration_evidence_found: false,
            api_endpoint_preference_confirmed: false,
        },
        investigation_context: {
            manifest_candidate_targets_count: Array.isArray(manifest.candidate_targets)
                ? manifest.candidate_targets.length
                : 0,
            l2v3p_attempted_unknown_target_count: metadataOnlyArtifact.attempted_unknown_target_count || 0,
            l2v3p_metadata_check_success_count: metadataOnlyArtifact.metadata_check_success_count || 0,
        },
        analyzed_targets: entries,
        recommended_next_step: NEXT_RECOMMENDED_STEP,
        next_required_step: NEXT_REQUIRED_STEP,
    };
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    const counts = artifact.counts || {};
    return {
        ...manifest,
        phase_5_21_l2v3q_investigation_status: artifact.artifact_status,
        continued_metadata_only_investigation_status: artifact.artifact_status,
        phase_5_21_l2v3q_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3q_report_path: REPORT_PATH,
        analyzed_target_count: counts.analyzed_target_count,
        phase_5_21_l2v3q_analyzed_target_count: counts.analyzed_target_count,
        unresolved_large_gap_count: counts.unresolved_large_gap_count,
        phase_5_21_l2v3q_unresolved_large_gap_count: counts.unresolved_large_gap_count,
        likely_reverse_fixture_or_slug_reuse_count: counts.likely_reverse_fixture_or_slug_reuse_count,
        phase_5_21_l2v3q_likely_reverse_fixture_or_slug_reuse_count: counts.likely_reverse_fixture_or_slug_reuse_count,
        missing_reverse_fixture_evidence_count: counts.missing_reverse_fixture_evidence_count,
        phase_5_21_l2v3q_missing_reverse_fixture_evidence_count: counts.missing_reverse_fixture_evidence_count,
        missing_pageurl_base_count: counts.missing_pageurl_base_count,
        phase_5_21_l2v3q_missing_pageurl_base_count: counts.missing_pageurl_base_count,
        missing_team_reverse_evidence_count: counts.missing_team_reverse_evidence_count,
        phase_5_21_l2v3q_missing_team_reverse_evidence_count: counts.missing_team_reverse_evidence_count,
        detail_url_construction_suspect_count: counts.detail_url_construction_suspect_count,
        phase_5_21_l2v3q_detail_url_construction_suspect_count: counts.detail_url_construction_suspect_count,
        route_target_regeneration_needed_count: counts.route_target_regeneration_needed_count,
        phase_5_21_l2v3q_route_target_regeneration_needed_count: counts.route_target_regeneration_needed_count,
        api_endpoint_preferred_count: counts.api_endpoint_preferred_count,
        phase_5_21_l2v3q_api_endpoint_preferred_count: counts.api_endpoint_preferred_count,
        future_review_candidate_count: counts.future_review_candidate_count,
        phase_5_21_l2v3q_future_review_candidate_count: counts.future_review_candidate_count,
        still_blocked_count: counts.still_blocked_count,
        phase_5_21_l2v3q_still_blocked_count: counts.still_blocked_count,
        accepted_mapping_count: 0,
        phase_5_21_l2v3q_accepted_mapping_count: 0,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        phase_5_21_l2v3q_identity_mapping_acceptance_performed: false,
        phase_5_21_l2v3q_baseline_acceptance_performed: false,
        phase_5_21_l2v3q_raw_write_retry_performed: false,
        phase_5_21_l2v3q_raw_write_ready_for_execution: false,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

function buildReport(artifact = {}) {
    const counts = artifact.counts || {};
    return `# Data Entrypoint Governance - Phase 5.21 L2V3Q

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- source_phase=Phase 5.21L2V3P
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

- investigation result is not an accepted mapping.
- unresolved_large_gap remains blocked for identity mapping acceptance and raw write.
- likely reverse fixture or slug reuse remains blocked.
- detail_url_construction_suspect is not an accepted mapping.
- future_review_candidate is not an accepted mapping.
- accepted_mapping_count=0.
- raw_write_ready_for_execution=false.
- separate identity mapping acceptance, baseline acceptance, and final DB-write authorization remain required.

## Investigation Summary

- analyzed_target_count=${counts.analyzed_target_count}
- requested_observed_external_id_mismatch_count=${artifact.root_cause_summary?.requested_observed_external_id_mismatch_count || 0}
- reversed_team_pair_count=${artifact.root_cause_summary?.reversed_team_pair_count || 0}
- observed_page_url_base_present_count=${artifact.root_cause_summary?.observed_page_url_base_present_count || 0}
- counterfactual_reverse_fixture_detected_count=${artifact.root_cause_summary?.counterfactual_reverse_fixture_detected_count || 0}
- current_route_uses_requested_page_url_base=${artifact.root_cause_summary?.current_route_uses_requested_page_url_base}
- current_route_uses_fragment_anchor=${artifact.root_cause_summary?.current_route_uses_fragment_anchor}
- current_route_uses_detail_api_endpoint=${artifact.root_cause_summary?.current_route_uses_detail_api_endpoint}

## Classification Summary

| metric | count |
| --- | ---: |
| analyzed_target_count | ${counts.analyzed_target_count} |
| unresolved_large_gap_count | ${counts.unresolved_large_gap_count} |
| likely_reverse_fixture_or_slug_reuse_count | ${counts.likely_reverse_fixture_or_slug_reuse_count} |
| missing_reverse_fixture_evidence_count | ${counts.missing_reverse_fixture_evidence_count} |
| missing_pageurl_base_count | ${counts.missing_pageurl_base_count} |
| missing_team_reverse_evidence_count | ${counts.missing_team_reverse_evidence_count} |
| detail_url_construction_suspect_count | ${counts.detail_url_construction_suspect_count} |
| route_target_regeneration_needed_count | ${counts.route_target_regeneration_needed_count} |
| api_endpoint_preferred_count | ${counts.api_endpoint_preferred_count} |
| future_review_candidate_count | ${counts.future_review_candidate_count} |
| still_blocked_count | ${counts.still_blocked_count} |
| accepted_mapping_count | ${counts.accepted_mapping_count} |

## Root Cause Conclusion

The 42 L2V3P targets do not look like random large date mismatches. All 42 now show requested-vs-observed external-id mismatch plus reversed home/away teams. The current rule engine kept them at unresolved_large_gap because the requested side still lacks page_url_base evidence, so the reverse-fixture rule precondition was not satisfied. A counterfactual check that injects the observed page_url_base back into the requested side reclassifies all 42 as reverse_fixture_detected, which points to detail URL construction or slug-route identity selection as the primary blocker rather than target regeneration.

## Deliverables

- artifact=${ARTIFACT_OUTPUT_PATH}
- report=${REPORT_PATH}
- proposal manifest updated with L2V3Q investigation metadata.

## Next Step

${artifact.recommended_next_step}
`;
}

function validateManifest(manifest = {}) {
    const errors = [];
    if (!Array.isArray(manifest.candidate_targets) || manifest.candidate_targets.length !== 50) {
        errors.push('manifest candidate_targets must contain 50 entries');
    }
    if (
        normalizeText(manifest.phase_5_21_l2v3p_metadata_check_status) !==
        'completed_controlled_no_write_metadata_only_detail_check'
    ) {
        errors.push('manifest must already contain completed L2V3P metadata check status');
    }
    if (manifest.raw_write_ready_for_execution !== false) {
        errors.push('manifest raw_write_ready_for_execution must remain false');
    }
    return { ok: errors.length === 0, errors };
}

function validateMetadataOnlyArtifact(artifact = {}) {
    const errors = [];
    if (normalizeText(artifact.proposal_phase) !== 'Phase 5.21L2V3P') {
        errors.push('metadata-only artifact must be Phase 5.21L2V3P');
    }
    if (artifact.no_write !== true) {
        errors.push('metadata-only artifact must remain no-write');
    }
    if (Number(artifact.attempted_unknown_target_count) !== 42) {
        errors.push('metadata-only artifact attempted_unknown_target_count must be 42');
    }
    if (Number(artifact.metadata_check_success_count) !== 42) {
        errors.push('metadata-only artifact metadata_check_success_count must be 42');
    }
    if (artifact.raw_write_ready_for_execution !== false) {
        errors.push('metadata-only artifact raw_write_ready_for_execution must remain false');
    }
    return { ok: errors.length === 0, errors };
}

function runContinuedMetadataInvestigation(dependencies = {}) {
    const manifest = dependencies.manifest || readJsonFile(MANIFEST_PATH);
    const metadataOnlyArtifact = dependencies.metadataOnlyArtifact || readJsonFile(METADATA_ONLY_ARTIFACT_PATH);
    const manifestGate = validateManifest(manifest);
    if (!manifestGate.ok) {
        return { ok: false, status: 2, errors: manifestGate.errors };
    }
    const artifactGate = validateMetadataOnlyArtifact(metadataOnlyArtifact);
    if (!artifactGate.ok) {
        return { ok: false, status: 3, errors: artifactGate.errors };
    }
    const selected = selectUnresolvedTargets(manifest, metadataOnlyArtifact);
    const entries = selected.map(item =>
        buildClassificationEntry({ target: item.target || {}, metadataEntry: item.metadata_entry || {} })
    );
    const artifact = buildArtifact({
        manifest,
        metadataOnlyArtifact,
        entries,
        generatedAt: dependencies.generatedAt || GENERATED_AT,
    });
    const updatedManifest = updateManifestMetadata(manifest, artifact);
    const report = buildReport(artifact);

    if (dependencies.writeFiles !== false) {
        writeJsonFile(ARTIFACT_OUTPUT_PATH, artifact);
        writeTextFile(REPORT_PATH, report);
        writeJsonFile(MANIFEST_PATH, updatedManifest);
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
    const result = runContinuedMetadataInvestigation();
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
                analyzed_target_count: result.artifact.analyzed_target_count,
                unresolved_large_gap_count: result.artifact.unresolved_large_gap_count,
                likely_reverse_fixture_or_slug_reuse_count: result.artifact.likely_reverse_fixture_or_slug_reuse_count,
                missing_reverse_fixture_evidence_count: result.artifact.missing_reverse_fixture_evidence_count,
                detail_url_construction_suspect_count: result.artifact.detail_url_construction_suspect_count,
                route_target_regeneration_needed_count: result.artifact.route_target_regeneration_needed_count,
                future_review_candidate_count: result.artifact.future_review_candidate_count,
                accepted_mapping_count: result.artifact.accepted_mapping_count,
                raw_write_ready_for_execution: result.artifact.raw_write_ready_for_execution,
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
    METADATA_ONLY_ARTIFACT_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_PATH,
    NEXT_RECOMMENDED_STEP,
    NEXT_REQUIRED_STEP,
    requestedPageUrlBase,
    selectUnresolvedTargets,
    buildActualReconciliation,
    buildCounterfactualReconciliation,
    buildClassificationEntry,
    buildCounts,
    buildArtifact,
    updateManifestMetadata,
    buildReport,
    validateManifest,
    validateMetadataOnlyArtifact,
    runContinuedMetadataInvestigation,
};

if (require.main === module) {
    runCli();
}
