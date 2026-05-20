#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const NORMALIZATION_PROPOSAL_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.schedule_detail_identity_normalization_proposal.phase521l2v3f.json';
const REVIEW_RESULT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.identity_mapping_acceptance_review_result.phase521l2v3k.json';
const VERIFICATION_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.expanded_date_rule_verification.phase521l2v3n.json';
const INVESTIGATION_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.continued_date_rule_investigation.phase521l2v3o.json';
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3O.md';
const PHASE = 'Phase 5.21L2V3O';
const PHASE_NAME = 'continued_expanded_date_rule_investigation';
const GENERATED_AT = '2026-05-20T00:00:00Z';
const NEXT_RECOMMENDED_STEP = 'Phase 5.21L2V3P: controlled no-write metadata-only detail check';
const INVESTIGATION_STATUS = 'completed_no_write_source_controlled_artifact_only';
const PATH_SELECTION = 'A_no_live_check_planning_only';
const PATH_SELECTION_REASON =
    'Current blockers are already explainable from source-controlled artifacts: L2V3F/L2V3K only cover 8 reviewed candidates, the remaining 42 were not evaluated there, and proposal candidate metadata does not persist page_url_base for those unknown targets.';

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

function normalizeBoolean(value) {
    return value === true;
}

function reviewEntryByScheduleId(reviewResult = {}) {
    const entries = Array.isArray(reviewResult.review_entries) ? reviewResult.review_entries : [];
    return new Map(entries.map(entry => [normalizeText(entry.schedule_external_id), entry]));
}

function buildNormalizationState(normalizationProposal = {}) {
    const checkedTargets = Array.isArray(normalizationProposal.checked_targets)
        ? normalizationProposal.checked_targets
        : [];
    const uncheckedTargets = Array.isArray(normalizationProposal.unchecked_targets)
        ? normalizationProposal.unchecked_targets
        : Array.isArray(normalizationProposal.targets_not_checked)
          ? normalizationProposal.targets_not_checked
          : [];

    const stateByScheduleId = new Map();

    for (const target of checkedTargets) {
        stateByScheduleId.set(normalizeText(target.requested_schedule_external_id), 'checked_in_l2v3f');
    }

    for (const target of uncheckedTargets) {
        stateByScheduleId.set(normalizeText(target.requested_schedule_external_id), 'not_evaluated_in_l2v3f');
    }

    return {
        checkedTargets,
        uncheckedTargets,
        stateByScheduleId,
    };
}

function requestedPageUrlBase(target = {}) {
    return (
        normalizeText(target.page_url_base) ||
        normalizeText(target.source_inventory_page_url_base) ||
        normalizeText(target.manifest_page_url_base) ||
        null
    );
}

function requestedScheduleDate(target = {}) {
    return normalizeText(target.match_date) || normalizeText(target.kickoff_time) || null;
}

function requestedTeamMetadataPresent(target = {}) {
    return Boolean(normalizeText(target.home_team) && normalizeText(target.away_team));
}

function assertControlledMetadataCheckNoWrite(options = {}) {
    if (
        normalizeBoolean(options.dbWriteRequested) ||
        normalizeBoolean(options.rawInsertRequested) ||
        normalizeBoolean(options.matchesWriteRequested) ||
        normalizeBoolean(options.matchesExternalIdModified)
    ) {
        throw new Error('Phase 5.21L2V3O controlled metadata check must remain no-write');
    }
    return true;
}

function buildClassificationLabels({
    target = {},
    unknownSummary = {},
    reviewEntry = null,
    normalizationState = 'not_evaluated_in_l2v3f',
} = {}) {
    const labels = [];
    const observedDetailMetadataPresent = Boolean(
        normalizeText(unknownSummary.observed_detail_external_id) || normalizeText(reviewEntry?.detail_external_id)
    );

    if (!observedDetailMetadataPresent) labels.push('missing_observed_detail_metadata');
    if (!requestedPageUrlBase(target)) labels.push('missing_page_url_base');
    if (!requestedScheduleDate(target)) labels.push('missing_schedule_date');
    if (!requestedTeamMetadataPresent(target)) labels.push('missing_team_metadata');
    if (!reviewEntry && normalizationState !== 'checked_in_l2v3f') labels.push('artifact_coverage_gap');
    if (
        !normalizeText(target.source_inventory_page_url_base) &&
        !normalizeText(target.page_url_base) &&
        !normalizeText(target.manifest_page_url_base)
    ) {
        labels.push('source_inventory_gap');
    }
    labels.push('not_checked_live');

    if (!labels.length) labels.push('unknown_reason');
    return labels;
}

function safeErrorSummary(labels = []) {
    if (labels.includes('missing_observed_detail_metadata') && labels.includes('artifact_coverage_gap')) {
        return 'Observed detail metadata is absent from source-controlled review artifacts; unknown remains blocked pending separate metadata collection.';
    }
    if (labels.includes('missing_page_url_base') && labels.includes('source_inventory_gap')) {
        return 'Source-controlled candidate metadata does not preserve page_url_base for this target; unknown remains blocked.';
    }
    return 'Unknown target remains blocked for identity mapping acceptance and raw write.';
}

function buildUnknownInvestigationEntry({
    target = {},
    unknownSummary = {},
    reviewEntriesByScheduleId = new Map(),
    normalizationStateByScheduleId = new Map(),
} = {}) {
    const scheduleExternalId = normalizeText(target.external_id);
    const reviewEntry = reviewEntriesByScheduleId.get(scheduleExternalId) || null;
    const normalizationState = normalizationStateByScheduleId.get(scheduleExternalId) || 'not_evaluated_in_l2v3f';
    const labels = buildClassificationLabels({
        target,
        unknownSummary,
        reviewEntry,
        normalizationState,
    });

    return {
        match_id: target.match_id,
        schedule_external_id: scheduleExternalId,
        requested_schedule_date: requestedScheduleDate(target),
        requested_status: normalizeText(target.status) || null,
        requested_home_team: normalizeText(target.home_team) || null,
        requested_away_team: normalizeText(target.away_team) || null,
        requested_team_metadata_present: requestedTeamMetadataPresent(target),
        requested_page_url_base_present: Boolean(requestedPageUrlBase(target)),
        source_inventory_page_url_base_present: Boolean(normalizeText(target.source_inventory_page_url_base)),
        manifest_page_url_base_present: Boolean(
            normalizeText(target.manifest_page_url_base) || normalizeText(target.page_url_base)
        ),
        requested_schedule_date_present: Boolean(requestedScheduleDate(target)),
        review_result_entry_present: Boolean(reviewEntry),
        l2v3f_normalization_state: normalizationState,
        observed_detail_external_id: normalizeText(unknownSummary.observed_detail_external_id) || null,
        observed_detail_metadata_present: false,
        date_rule_status: normalizeText(unknownSummary.date_rule_status) || 'unknown',
        raw_write_blocker_status: 'blocked',
        identity_mapping_acceptance_blocker_status: 'blocked',
        classification_labels: labels,
        primary_reason: labels[0],
        controlled_metadata_check_status: 'not_performed',
        accepted_mapping: false,
        raw_write_authorized: false,
        safe_to_consider_for_future_review: false,
        safe_error_summary: safeErrorSummary(labels),
    };
}

function countByLabel(entries = [], label) {
    return entries.filter(
        entry => Array.isArray(entry.classification_labels) && entry.classification_labels.includes(label)
    ).length;
}

function buildCounts(entries = []) {
    return {
        checked_unknown_target_count: entries.length,
        missing_observed_detail_metadata_count: countByLabel(entries, 'missing_observed_detail_metadata'),
        missing_page_url_base_count: countByLabel(entries, 'missing_page_url_base'),
        missing_schedule_date_count: countByLabel(entries, 'missing_schedule_date'),
        missing_team_metadata_count: countByLabel(entries, 'missing_team_metadata'),
        not_checked_live_count: countByLabel(entries, 'not_checked_live'),
        source_inventory_gap_count: countByLabel(entries, 'source_inventory_gap'),
        artifact_coverage_gap_count: countByLabel(entries, 'artifact_coverage_gap'),
        controlled_metadata_check_performed: false,
        metadata_check_success_count: 0,
        metadata_check_blocked_count: 0,
        metadata_check_failed_count: 0,
        still_unknown_count: entries.length,
        newly_classified_reverse_fixture_count: 0,
        newly_classified_date_match_count: 0,
        newly_classified_same_utc_day_count: 0,
        newly_classified_unresolved_large_gap_count: 0,
        raw_write_blocked_count: entries.length,
        identity_mapping_acceptance_blocked_count: entries.length,
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
    };
}

function buildArtifact({
    manifest,
    normalizationProposal,
    reviewResult,
    verificationArtifact,
    generatedAt = GENERATED_AT,
} = {}) {
    const targets = Array.isArray(manifest?.candidate_targets) ? manifest.candidate_targets : [];
    const reviewEntriesByScheduleId = reviewEntryByScheduleId(reviewResult);
    const normalizationState = buildNormalizationState(normalizationProposal);
    const unknownSummaryByScheduleId = new Map(
        (Array.isArray(verificationArtifact?.target_summaries) ? verificationArtifact.target_summaries : [])
            .filter(summary => normalizeText(summary.date_rule_status) === 'unknown')
            .map(summary => [normalizeText(summary.schedule_external_id), summary])
    );

    const unknownTargets = targets.filter(target => unknownSummaryByScheduleId.has(normalizeText(target.external_id)));
    const unknownTargetInvestigation = unknownTargets.map(target =>
        buildUnknownInvestigationEntry({
            target,
            unknownSummary: unknownSummaryByScheduleId.get(normalizeText(target.external_id)),
            reviewEntriesByScheduleId,
            normalizationStateByScheduleId: normalizationState.stateByScheduleId,
        })
    );
    const counts = buildCounts(unknownTargetInvestigation);

    return {
        artifact_type: 'continued_date_rule_investigation',
        artifact_status: INVESTIGATION_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        source_phase: 'Phase 5.21L2V3N',
        generated_at: generatedAt,
        no_write: true,
        planning_only: true,
        source_controlled_artifact_only: true,
        path_selected: PATH_SELECTION,
        path_selection_reason: PATH_SELECTION_REASON,
        controlled_metadata_check_performed: false,
        live_source_check_performed: false,
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
        raw_data_or_pageprops_payload_saved: false,
        raw_data_or_pageprops_payload_printed: false,
        classification_dimensions_overlap: true,
        counts,
        ...counts,
        safety_contract: {
            investigation_result_is_not_accepted_mapping: true,
            metadata_only_check_result_is_not_accepted_mapping: true,
            metadata_check_success_does_not_equal_raw_write_ready: true,
            unknown_blocks_identity_mapping_acceptance: true,
            unknown_blocks_raw_write: true,
            unknown_cannot_be_considered_safe: true,
            unknown_cannot_be_accepted: true,
            separate_identity_mapping_acceptance_required: true,
            separate_baseline_acceptance_required: true,
            separate_final_db_write_authorization_required: true,
        },
        source_artifacts: {
            proposal_manifest_path: MANIFEST_PATH,
            l2v3f_normalization_proposal_path: NORMALIZATION_PROPOSAL_PATH,
            l2v3k_identity_mapping_review_result_path: REVIEW_RESULT_PATH,
            l2v3n_expanded_verification_artifact_path: VERIFICATION_ARTIFACT_PATH,
        },
        investigation_findings: {
            manifest_candidate_targets_count: targets.length,
            l2v3f_checked_targets_count: normalizationState.checkedTargets.length,
            l2v3f_unchecked_targets_count: normalizationState.uncheckedTargets.length,
            l2v3k_review_entries_count: Array.isArray(reviewResult?.review_entries)
                ? reviewResult.review_entries.length
                : 0,
            l2v3n_unknown_count: verificationArtifact?.unknown_count || counts.still_unknown_count,
            known_reverse_fixture_targets_still_blocked_count:
                verificationArtifact?.reverse_fixture_detected_count || 0,
            all_candidate_targets_still_blocked_count: verificationArtifact?.raw_write_blocked_count || 0,
            manifest_candidate_targets_missing_page_url_base_count: targets.filter(
                target => !requestedPageUrlBase(target)
            ).length,
            unknown_targets_with_requested_schedule_date_count: unknownTargetInvestigation.filter(entry =>
                normalizeBoolean(entry.requested_schedule_date_present)
            ).length,
            unknown_targets_with_requested_team_metadata_count: unknownTargetInvestigation.filter(entry =>
                normalizeBoolean(entry.requested_team_metadata_present)
            ).length,
        },
        unknown_target_investigation: unknownTargetInvestigation,
        recommended_next_step: NEXT_RECOMMENDED_STEP,
    };
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    const counts = artifact.counts || {};
    return {
        ...manifest,
        phase_5_21_l2v3o_investigation_status: INVESTIGATION_STATUS,
        continued_expanded_date_rule_investigation_status: INVESTIGATION_STATUS,
        phase_5_21_l2v3o_artifact_path: INVESTIGATION_ARTIFACT_PATH,
        phase_5_21_l2v3o_report_path: REPORT_PATH,
        phase_5_21_l2v3o_path_selected: PATH_SELECTION,
        checked_unknown_target_count: counts.checked_unknown_target_count,
        phase_5_21_l2v3o_checked_unknown_target_count: counts.checked_unknown_target_count,
        missing_observed_detail_metadata_count: counts.missing_observed_detail_metadata_count,
        phase_5_21_l2v3o_missing_observed_detail_metadata_count: counts.missing_observed_detail_metadata_count,
        missing_page_url_base_count: counts.missing_page_url_base_count,
        phase_5_21_l2v3o_missing_page_url_base_count: counts.missing_page_url_base_count,
        missing_schedule_date_count: counts.missing_schedule_date_count,
        phase_5_21_l2v3o_missing_schedule_date_count: counts.missing_schedule_date_count,
        missing_team_metadata_count: counts.missing_team_metadata_count,
        phase_5_21_l2v3o_missing_team_metadata_count: counts.missing_team_metadata_count,
        not_checked_live_count: counts.not_checked_live_count,
        phase_5_21_l2v3o_not_checked_live_count: counts.not_checked_live_count,
        source_inventory_gap_count: counts.source_inventory_gap_count,
        phase_5_21_l2v3o_source_inventory_gap_count: counts.source_inventory_gap_count,
        artifact_coverage_gap_count: counts.artifact_coverage_gap_count,
        phase_5_21_l2v3o_artifact_coverage_gap_count: counts.artifact_coverage_gap_count,
        controlled_metadata_check_performed: false,
        phase_5_21_l2v3o_controlled_metadata_check_performed: false,
        still_unknown_count: counts.still_unknown_count,
        phase_5_21_l2v3o_still_unknown_count: counts.still_unknown_count,
        phase_5_21_l2v3o_accepted_mapping_count: 0,
        phase_5_21_l2v3o_identity_mapping_acceptance_performed: false,
        phase_5_21_l2v3o_baseline_acceptance_performed: false,
        phase_5_21_l2v3o_raw_write_retry_performed: false,
        phase_5_21_l2v3o_raw_write_ready_for_execution: false,
        phase_5_21_l2v3o_raw_write_blocked_count: counts.raw_write_blocked_count,
        phase_5_21_l2v3o_identity_mapping_acceptance_blocked_count: counts.identity_mapping_acceptance_blocked_count,
        accepted_mapping_count: 0,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        recommended_next_step: artifact.recommended_next_step,
    };
}

function buildReport(artifact = {}) {
    const counts = artifact.counts || {};
    const findings = artifact.investigation_findings || {};

    return `# Data Entrypoint Governance - Phase 5.21 L2V3O

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- source_phase=Phase 5.21L2V3N
- branch=data/pageprops-v2-continued-date-rule-investigation-phase521l2v3o
- path_selected=${PATH_SELECTION}
- controlled_metadata_check_performed=false
- live_source_check_performed=false
- db_write_performed=false
- raw_insert_performed=false
- matches_write_performed=false
- matches_external_id_modified=false
- schema_migration_performed=false
- parser_features_training_prediction_performed=false

## Path Selection

- selected_path=A no live check, source-controlled artifact analysis only.
- selection_reason=${PATH_SELECTION_REASON}

## Safety Contract

- investigation result is not an accepted mapping.
- metadata-only check result is not an accepted mapping.
- metadata_check_success does not equal raw_write_ready_for_execution.
- unknown blocks identity mapping acceptance.
- unknown blocks raw write.
- accepted_mapping_count=0.
- raw_write_ready_for_execution=false.
- separate identity mapping acceptance, baseline acceptance, and final DB-write authorization are still required.

## Source Coverage Findings

- manifest_candidate_targets_count=${findings.manifest_candidate_targets_count}
- l2v3f_checked_targets_count=${findings.l2v3f_checked_targets_count}
- l2v3f_unchecked_targets_count=${findings.l2v3f_unchecked_targets_count}
- l2v3k_review_entries_count=${findings.l2v3k_review_entries_count}
- l2v3n_unknown_count=${findings.l2v3n_unknown_count}
- known_reverse_fixture_targets_still_blocked_count=${findings.known_reverse_fixture_targets_still_blocked_count}
- all_candidate_targets_still_blocked_count=${findings.all_candidate_targets_still_blocked_count}
- manifest_candidate_targets_missing_page_url_base_count=${findings.manifest_candidate_targets_missing_page_url_base_count}
- unknown_targets_with_requested_schedule_date_count=${findings.unknown_targets_with_requested_schedule_date_count}
- unknown_targets_with_requested_team_metadata_count=${findings.unknown_targets_with_requested_team_metadata_count}

## Classification Summary

| metric | count |
| --- | ---: |
| checked_unknown_target_count | ${counts.checked_unknown_target_count} |
| missing_observed_detail_metadata_count | ${counts.missing_observed_detail_metadata_count} |
| missing_page_url_base_count | ${counts.missing_page_url_base_count} |
| missing_schedule_date_count | ${counts.missing_schedule_date_count} |
| missing_team_metadata_count | ${counts.missing_team_metadata_count} |
| not_checked_live_count | ${counts.not_checked_live_count} |
| source_inventory_gap_count | ${counts.source_inventory_gap_count} |
| artifact_coverage_gap_count | ${counts.artifact_coverage_gap_count} |
| metadata_check_success_count | ${counts.metadata_check_success_count} |
| metadata_check_blocked_count | ${counts.metadata_check_blocked_count} |
| metadata_check_failed_count | ${counts.metadata_check_failed_count} |
| still_unknown_count | ${counts.still_unknown_count} |
| newly_classified_reverse_fixture_count | ${counts.newly_classified_reverse_fixture_count} |
| newly_classified_date_match_count | ${counts.newly_classified_date_match_count} |
| newly_classified_same_utc_day_count | ${counts.newly_classified_same_utc_day_count} |
| newly_classified_unresolved_large_gap_count | ${counts.newly_classified_unresolved_large_gap_count} |
| raw_write_blocked_count | ${counts.raw_write_blocked_count} |
| identity_mapping_acceptance_blocked_count | ${counts.identity_mapping_acceptance_blocked_count} |
| accepted_mapping_count | ${counts.accepted_mapping_count} |

## Investigation Result

The 42 unknown targets remain blocked because source-controlled artifacts do not contain observed detail metadata for them, L2V3F/L2V3K only cover the 8 known reverse-fixture candidates, and L2V3N intentionally avoided any live detail check. The requested schedule date and requested team metadata are already present for the unknown targets, so the missing evidence is concentrated around observed detail metadata and pageUrl-base coverage, not around the schedule-side basics. The prior 8 reverse-fixture candidates remain blocked as separate known mismatches, so all 50 candidate targets are still blocked overall.

## Deliverables

- artifact=${INVESTIGATION_ARTIFACT_PATH}
- report=${REPORT_PATH}
- proposal manifest updated with L2V3O continued investigation metadata.

## Next Step

${artifact.recommended_next_step}
`;
}

function run() {
    assertControlledMetadataCheckNoWrite();

    const manifest = readJsonFile(MANIFEST_PATH);
    const normalizationProposal = readJsonFile(NORMALIZATION_PROPOSAL_PATH);
    const reviewResult = readJsonFile(REVIEW_RESULT_PATH);
    const verificationArtifact = readJsonFile(VERIFICATION_ARTIFACT_PATH);
    const artifact = buildArtifact({
        manifest,
        normalizationProposal,
        reviewResult,
        verificationArtifact,
    });
    const updatedManifest = updateManifestMetadata(manifest, artifact);

    writeJsonFile(INVESTIGATION_ARTIFACT_PATH, artifact);
    writeTextFile(REPORT_PATH, buildReport(artifact));
    writeJsonFile(MANIFEST_PATH, updatedManifest);
    console.log(
        JSON.stringify(
            {
                phase: PHASE,
                artifact: INVESTIGATION_ARTIFACT_PATH,
                report: REPORT_PATH,
                checked_unknown_target_count: artifact.checked_unknown_target_count,
                missing_observed_detail_metadata_count: artifact.missing_observed_detail_metadata_count,
                artifact_coverage_gap_count: artifact.artifact_coverage_gap_count,
                still_unknown_count: artifact.still_unknown_count,
                accepted_mapping_count: artifact.accepted_mapping_count,
                raw_write_ready_for_execution: artifact.raw_write_ready_for_execution,
            },
            null,
            2
        )
    );
}

if (require.main === module) {
    run();
}

module.exports = {
    MANIFEST_PATH,
    NORMALIZATION_PROPOSAL_PATH,
    REVIEW_RESULT_PATH,
    VERIFICATION_ARTIFACT_PATH,
    INVESTIGATION_ARTIFACT_PATH,
    REPORT_PATH,
    buildArtifact,
    buildUnknownInvestigationEntry,
    buildCounts,
    updateManifestMetadata,
    buildReport,
    assertControlledMetadataCheckNoWrite,
};
