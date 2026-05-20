#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const {
    reconcileRouteIdentity,
    assertRawWriteIdentityGate,
} = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const REVIEW_RESULT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.identity_mapping_acceptance_review_result.phase521l2v3k.json';
const L2V3M_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.date_mismatch_rule_implementation.phase521l2v3m.json';
const L2V3L_PLAN_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.date_mismatch_resolution_plan.phase521l2v3l.json';
const VERIFICATION_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.expanded_date_rule_verification.phase521l2v3n.json';
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3N.md';
const PHASE = 'Phase 5.21L2V3N';
const PHASE_NAME = 'expanded_no_write_date_rule_verification_across_50_targets';
const GENERATED_AT = '2026-05-20T00:00:00Z';
const TARGET_COUNT = 50;
const RAW_VERSION = 'fotmob_pageprops_v2';
const HASH_STRATEGY = 'stable_pageprops_payload_v1';
const BLOCKING_DATE_STATUSES = new Set([
    'reverse_fixture_detected',
    'cross_season_slug_reuse',
    'unresolved_large_gap',
    'unknown',
]);
const SAFE_REVIEW_DATE_STATUSES = new Set([
    'date_match',
    'same_utc_day',
    'timezone_only_mismatch',
    'postponed_or_rescheduled_explained',
]);
const DATE_RULE_STATUSES = Object.freeze([
    'date_match',
    'same_utc_day',
    'timezone_only_mismatch',
    'postponed_or_rescheduled_explained',
    'reverse_fixture_detected',
    'cross_season_slug_reuse',
    'unresolved_large_gap',
    'unknown',
]);

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

function reviewEntryByScheduleId(reviewResult = {}) {
    const entries = Array.isArray(reviewResult.review_entries) ? reviewResult.review_entries : [];
    return new Map(entries.map(entry => [normalizeText(entry.schedule_external_id), entry]));
}

function requestedPageUrlBase(target = {}, reviewEntry = null) {
    return (
        normalizeText(reviewEntry?.page_url_base) ||
        normalizeText(target.page_url_base) ||
        normalizeText(target.source_inventory_page_url_base) ||
        normalizeText(target.manifest_page_url_base) ||
        null
    );
}

function buildReconciliationInput(target = {}, reviewEntry = null) {
    const hasReviewEntry = Boolean(reviewEntry);
    return {
        requestedScheduleExternalId: target.external_id,
        requestedPageUrlBase: requestedPageUrlBase(target, reviewEntry),
        requestedHomeTeam: target.home_team,
        requestedAwayTeam: target.away_team,
        requestedMatchDate: target.match_date || target.kickoff_time,
        requestedStatus: target.status,
        requestedSeason: target.season,
        observedDetailExternalId: hasReviewEntry ? reviewEntry.detail_external_id : null,
        observedPageUrlBase: hasReviewEntry ? reviewEntry.page_url_base : null,
        observedHomeTeam: hasReviewEntry ? reviewEntry.away_team : null,
        observedAwayTeam: hasReviewEntry ? reviewEntry.home_team : null,
        observedMatchDate: hasReviewEntry ? reviewEntry.detail_match_date : null,
        observedStatus: hasReviewEntry ? target.status || 'finished' : null,
        observedSeason: hasReviewEntry ? reviewEntry.season : null,
        acceptedIdentityMappingPresent: false,
        proposalOnlyMapping: hasReviewEntry,
    };
}

function teamPairMatchStatus(reconciliation = {}) {
    const result = reconciliation.date_compatibility_result || {};
    if (result.reversed_home_away === true) return 'same_pair_reversed_home_away_order';
    if (result.same_pair_any_order === true) return 'same_pair_same_home_away_order';
    if (!reconciliation.observed_detail_external_id) return 'missing_observed_team_pair';
    return 'different_or_unknown';
}

function safeErrorSummary(reconciliation = {}, reviewEntry = null) {
    if (reconciliation.date_compatibility_status === 'reverse_fixture_detected') {
        return 'source-controlled review metadata indicates same pageUrl base, reversed teams, and large date gap; blocked as identity mismatch';
    }
    if (!reviewEntry) {
        return 'observed detail metadata is unavailable in source-controlled artifacts; date rule status remains unknown and blocked';
    }
    if (BLOCKING_DATE_STATUSES.has(reconciliation.date_compatibility_status)) {
        return `${reconciliation.date_compatibility_status} blocks identity mapping acceptance and raw write`;
    }
    return 'safe metadata only; still not an accepted mapping or raw write authorization';
}

function buildTargetSummary(target = {}, reviewEntry = null) {
    const reconciliation = reconcileRouteIdentity(buildReconciliationInput(target, reviewEntry));
    const gate = assertRawWriteIdentityGate(reconciliation);
    const dateStatus = reconciliation.date_compatibility_status;
    const dateRuleBlocksAcceptance =
        reconciliation.date_compatibility_result?.blocks_identity_mapping_acceptance === true;
    const missingAcceptedMapping = reconciliation.accepted_identity_mapping_present !== true;
    const safeToConsiderForFutureReview =
        SAFE_REVIEW_DATE_STATUSES.has(dateStatus) &&
        !BLOCKING_DATE_STATUSES.has(dateStatus) &&
        reconciliation.schedule_external_id_vs_detail_external_id_status !== 'unknown';

    return {
        match_id: target.match_id,
        schedule_external_id: normalizeText(target.external_id),
        observed_detail_external_id: reconciliation.observed_detail_external_id || null,
        schedule_date: target.match_date || target.kickoff_time || null,
        detail_date: reviewEntry?.detail_match_date || null,
        page_url_base_match_status: reconciliation.page_url_base_match_status,
        team_pair_match_status: teamPairMatchStatus(reconciliation),
        date_rule_status: dateStatus,
        raw_write_blocker_status: gate.ok ? 'not_blocked_by_date_rule_but_not_authorized' : 'blocked',
        identity_mapping_acceptance_blocker_status:
            dateRuleBlocksAcceptance || missingAcceptedMapping ? 'blocked' : 'not_blocked_by_date_rule',
        accepted_mapping: false,
        raw_write_authorized: false,
        raw_write_blocked: gate.ok === false,
        review_blocked: gate.ok === false || BLOCKING_DATE_STATUSES.has(dateStatus),
        safe_to_consider_for_future_review: safeToConsiderForFutureReview,
        safety_blockers: reconciliation.safety_blockers,
        safe_error_summary: safeErrorSummary(reconciliation, reviewEntry),
    };
}

function emptyStatusCounts() {
    return Object.fromEntries(DATE_RULE_STATUSES.map(status => [`${status}_count`, 0]));
}

function buildCounts(targetSummaries = []) {
    const counts = {
        checked_target_count: targetSummaries.length,
        ...emptyStatusCounts(),
        raw_write_blocked_count: 0,
        identity_mapping_acceptance_blocked_count: 0,
        safe_to_consider_for_future_review_count: 0,
        accepted_mapping_count: 0,
        review_blocked_count: 0,
    };

    for (const summary of targetSummaries) {
        const statusKey = `${summary.date_rule_status}_count`;
        counts[statusKey] = (counts[statusKey] || 0) + 1;
        if (summary.raw_write_blocked) counts.raw_write_blocked_count += 1;
        if (summary.identity_mapping_acceptance_blocker_status === 'blocked') {
            counts.identity_mapping_acceptance_blocked_count += 1;
        }
        if (summary.safe_to_consider_for_future_review) counts.safe_to_consider_for_future_review_count += 1;
        if (summary.accepted_mapping) counts.accepted_mapping_count += 1;
        if (summary.review_blocked) counts.review_blocked_count += 1;
    }
    return counts;
}

function buildArtifact({ manifest, reviewResult, l2v3mArtifact, generatedAt = GENERATED_AT } = {}) {
    const targets = Array.isArray(manifest?.candidate_targets) ? manifest.candidate_targets : [];
    const reviewEntriesByScheduleId = reviewEntryByScheduleId(reviewResult);
    const targetSummaries = targets.map(target =>
        buildTargetSummary(target, reviewEntriesByScheduleId.get(normalizeText(target.external_id)) || null)
    );
    const counts = buildCounts(targetSummaries);
    const knownMappings = targetSummaries
        .filter(summary => summary.date_rule_status === 'reverse_fixture_detected')
        .map(summary => ({
            schedule_external_id: summary.schedule_external_id,
            detail_external_id: summary.observed_detail_external_id,
            classification: summary.date_rule_status,
            accepted_mapping: false,
            raw_write_blocked: summary.raw_write_blocked,
            review_blocked: summary.review_blocked,
        }));

    return {
        artifact_type: 'expanded_date_rule_verification',
        artifact_status: 'completed_no_write_source_controlled_metadata_only',
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        source_phase: 'Phase 5.21L2V3M',
        generated_at: generatedAt,
        no_write: true,
        source_controlled_metadata_only: true,
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
        target_count_expected: TARGET_COUNT,
        raw_data_version: RAW_VERSION,
        hash_strategy: HASH_STRATEGY,
        date_rule_engine_statuses: l2v3mArtifact?.date_rule_engine_statuses || DATE_RULE_STATUSES,
        blocking_statuses: l2v3mArtifact?.blocking_statuses || [...BLOCKING_DATE_STATUSES],
        counts,
        ...counts,
        verification_contract: {
            expanded_verification_result_is_not_accepted_mapping: true,
            date_match_is_not_accepted_mapping: true,
            same_utc_day_is_not_accepted_mapping: true,
            safe_to_consider_for_future_review_is_not_accepted_mapping: true,
            reverse_fixture_detected_blocks_acceptance_and_raw_write: true,
            unresolved_large_gap_blocks_acceptance_and_raw_write: true,
            unknown_blocks_acceptance_and_raw_write: true,
            pageurl_base_match_alone_blocks_acceptance: true,
        },
        source_artifacts: {
            proposal_manifest_path: MANIFEST_PATH,
            l2v3m_date_rule_implementation_artifact_path: L2V3M_ARTIFACT_PATH,
            l2v3l_date_mismatch_resolution_plan_path: L2V3L_PLAN_PATH,
            l2v3k_identity_mapping_review_result_path: REVIEW_RESULT_PATH,
        },
        known_mappings_classification: knownMappings,
        target_summaries: targetSummaries,
        separate_authorization_still_required: {
            requires_separate_identity_mapping_acceptance: true,
            requires_separate_baseline_acceptance: true,
            requires_separate_final_db_write_authorization: true,
        },
        recommended_next_step: 'Phase 5.21L2V3O: continued expanded date rule investigation',
    };
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    const counts = artifact.counts || {};
    return {
        ...manifest,
        phase_5_21_l2v3n_verification_status: 'completed_no_write_source_controlled_metadata_only',
        expanded_date_rule_verification_status: 'completed_no_write_source_controlled_metadata_only',
        expanded_date_rule_verification_artifact_path: VERIFICATION_ARTIFACT_PATH,
        phase_5_21_l2v3n_report_path: REPORT_PATH,
        phase_5_21_l2v3n_checked_target_count: counts.checked_target_count,
        checked_target_count: counts.checked_target_count,
        date_match_count: counts.date_match_count,
        same_utc_day_count: counts.same_utc_day_count,
        timezone_only_mismatch_count: counts.timezone_only_mismatch_count,
        postponed_or_rescheduled_explained_count: counts.postponed_or_rescheduled_explained_count,
        reverse_fixture_detected_count: counts.reverse_fixture_detected_count,
        cross_season_slug_reuse_count: counts.cross_season_slug_reuse_count,
        unresolved_large_gap_count: counts.unresolved_large_gap_count,
        unknown_count: counts.unknown_count,
        raw_write_blocked_count: counts.raw_write_blocked_count,
        identity_mapping_acceptance_blocked_count: counts.identity_mapping_acceptance_blocked_count,
        safe_to_consider_for_future_review_count: counts.safe_to_consider_for_future_review_count,
        accepted_mapping_count: 0,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        phase_5_21_l2v3n_identity_mapping_acceptance_performed: false,
        phase_5_21_l2v3n_baseline_acceptance_performed: false,
        phase_5_21_l2v3n_raw_write_retry_performed: false,
        phase_5_21_l2v3n_raw_write_ready_for_execution: false,
        phase_5_21_l2v3n_accepted_mapping_count: 0,
        phase_5_21_l2v3n_live_source_check_performed: false,
        recommended_next_step: artifact.recommended_next_step,
    };
}

function buildReport(artifact = {}) {
    const counts = artifact.counts || {};
    const reverseRows = artifact.known_mappings_classification
        .map(
            item =>
                `| ${item.schedule_external_id} | ${item.detail_external_id} | ${item.classification} | ${item.accepted_mapping} | ${item.raw_write_blocked ? 'blocked' : 'not_blocked'} |`
        )
        .join('\n');

    return `# Data Entrypoint Governance - Phase 5.21 L2V3N

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- source_phase=Phase 5.21L2V3M
- branch=data/pageprops-v2-expanded-date-rule-verification-phase521l2v3n
- mode=no-write source-controlled metadata verification
- live_source_check_performed=false
- db_write_performed=false
- raw_insert_performed=false
- matches_write_performed=false
- matches_external_id_modified=false
- schema_migration_performed=false
- parser_features_training_prediction_performed=false

## Safety Contract

- expanded verification result is not an accepted mapping.
- date_match is not an accepted mapping.
- same_utc_day is not an accepted mapping.
- safe_to_consider_for_future_review is not an accepted mapping.
- reverse_fixture_detected blocks identity mapping acceptance and raw write.
- unresolved_large_gap blocks identity mapping acceptance and raw write.
- unknown date status blocks identity mapping acceptance and raw write.
- raw_write_ready_for_execution=false.
- accepted_mapping_count=0.
- separate identity mapping acceptance, baseline acceptance, and final DB-write authorization are still required.

## Verification Inputs

- manifest=${MANIFEST_PATH}
- l2v3m_artifact=${L2V3M_ARTIFACT_PATH}
- l2v3l_plan=${L2V3L_PLAN_PATH}
- l2v3k_review_result=${REVIEW_RESULT_PATH}

## Classification Summary

| metric | count |
| --- | ---: |
| checked_target_count | ${counts.checked_target_count} |
| date_match_count | ${counts.date_match_count} |
| same_utc_day_count | ${counts.same_utc_day_count} |
| timezone_only_mismatch_count | ${counts.timezone_only_mismatch_count} |
| postponed_or_rescheduled_explained_count | ${counts.postponed_or_rescheduled_explained_count} |
| reverse_fixture_detected_count | ${counts.reverse_fixture_detected_count} |
| cross_season_slug_reuse_count | ${counts.cross_season_slug_reuse_count} |
| unresolved_large_gap_count | ${counts.unresolved_large_gap_count} |
| unknown_count | ${counts.unknown_count} |
| raw_write_blocked_count | ${counts.raw_write_blocked_count} |
| identity_mapping_acceptance_blocked_count | ${counts.identity_mapping_acceptance_blocked_count} |
| safe_to_consider_for_future_review_count | ${counts.safe_to_consider_for_future_review_count} |
| accepted_mapping_count | ${counts.accepted_mapping_count} |

## Known Reverse Fixture Classifications

| schedule_external_id | observed_detail_external_id | classification | accepted_mapping | raw_write |
| --- | --- | --- | --- | --- |
${reverseRows}

## Expanded Verification Result

The 8 L2V3L known mappings remain blocked as reverse_fixture_detected. The remaining 42 candidate targets do not have observed detail metadata in source-controlled artifacts, so they remain unknown and blocked. No live detail check was performed in this phase.

## Deliverables

- artifact=${VERIFICATION_ARTIFACT_PATH}
- report=${REPORT_PATH}
- proposal manifest updated with L2V3N no-write verification metadata.

## Next Step

${artifact.recommended_next_step}
`;
}

function run() {
    const manifest = readJsonFile(MANIFEST_PATH);
    const reviewResult = readJsonFile(REVIEW_RESULT_PATH);
    const l2v3mArtifact = readJsonFile(L2V3M_ARTIFACT_PATH);
    const artifact = buildArtifact({ manifest, reviewResult, l2v3mArtifact });
    const updatedManifest = updateManifestMetadata(manifest, artifact);

    writeJsonFile(VERIFICATION_ARTIFACT_PATH, artifact);
    writeTextFile(REPORT_PATH, buildReport(artifact));
    writeJsonFile(MANIFEST_PATH, updatedManifest);
    console.log(
        JSON.stringify(
            {
                phase: PHASE,
                artifact: VERIFICATION_ARTIFACT_PATH,
                report: REPORT_PATH,
                checked_target_count: artifact.checked_target_count,
                reverse_fixture_detected_count: artifact.reverse_fixture_detected_count,
                unknown_count: artifact.unknown_count,
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
    REVIEW_RESULT_PATH,
    L2V3M_ARTIFACT_PATH,
    L2V3L_PLAN_PATH,
    VERIFICATION_ARTIFACT_PATH,
    REPORT_PATH,
    DATE_RULE_STATUSES,
    BLOCKING_DATE_STATUSES,
    buildArtifact,
    buildTargetSummary,
    buildCounts,
    updateManifestMetadata,
    buildReport,
};
