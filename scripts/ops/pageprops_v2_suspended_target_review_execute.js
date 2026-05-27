#!/usr/bin/env node
'use strict';

/* eslint-disable max-lines, complexity -- L2V3BA keeps local no-write review evidence explicit for governance review. */

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3BA';
const PHASE_NAME = 'controlled_no_write_suspended_target_review_execution';
const EXECUTION_STATUS = 'completed_controlled_no_write_suspended_target_review_execution';
const NEXT_STEP = 'Phase 5.21L2V3BB: expanded blocked target review planning';
const NEXT_REQUIRED_STEP = 'expanded_blocked_target_review_planning';
const PROPOSAL_MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const AZ_PLAN_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.suspended_target_review_plan.phase521l2v3az.json';
const AT_SUSPENSION_RESULT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.accepted_mapping_baseline_suspension_result.phase521l2v3at.json';
const AR_CONTRADICTION_RESULT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.accepted_mapping_baseline_contradiction_review_result.phase521l2v3ar.json';
const AY_REGRESSION_RESULT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.identity_contract_regression_result.phase521l2v3ay.json';
const AP_BLOCKER_INVESTIGATION_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.no_write_payload_recapture_blocker_investigation.phase521l2v3ap.json';
const Y_SOURCE_INVENTORY_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.controlled_source_inventory_acquisition_result.phase521l2v3y.json';
const V_SOURCE_ENRICHMENT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.source_inventory_enrichment_implementation.phase521l2v3v.json';
const N_DATE_RULE_VERIFICATION_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.expanded_date_rule_verification.phase521l2v3n.json';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.suspended_target_review_result.phase521l2v3ba.json';
const REPORT_OUTPUT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3BA.md';
const PROPOSAL_INSERTION_ANCHOR =
    '    "recommended_next_step_after_l2v3az": "Phase 5.21L2V3BA: controlled no-write suspended target review execution"';
const FALLBACK_PROPOSAL_INSERTION_ANCHOR =
    '    "recommended_next_step_after_l2v3ay": "Phase 5.21L2V3AZ: controlled no-write suspended target review planning"';
const ALLOWED_DECISIONS = Object.freeze([
    'remain_suspended',
    'eligible_for_re_acceptance_review',
    'requires_runner_contract_followup',
    'requires_expanded_evidence',
    'reject_mapping',
    'supersede_mapping',
]);
const PROHIBITED_DECISIONS = Object.freeze([
    'accepted',
    'reaccepted',
    'baseline_accepted',
    'raw_write_ready',
    'suspension_reversed',
    'rollback_performed',
]);
const REVIEWED_INPUTS = Object.freeze([
    ['az_suspended_target_review_plan', AZ_PLAN_PATH],
    ['at_suspension_result', AT_SUSPENSION_RESULT_PATH],
    ['ar_contradiction_review_result', AR_CONTRADICTION_RESULT_PATH],
    ['ay_identity_contract_regression_result', AY_REGRESSION_RESULT_PATH],
    ['ap_no_write_recapture_blocker_investigation', AP_BLOCKER_INVESTIGATION_PATH],
    ['y_source_inventory_acquisition_result', Y_SOURCE_INVENTORY_PATH],
    ['v_source_inventory_enrichment_implementation', V_SOURCE_ENRICHMENT_PATH],
    ['n_expanded_date_rule_verification', N_DATE_RULE_VERIFICATION_PATH],
    ['proposal_manifest', PROPOSAL_MANIFEST_PATH],
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

function readExistingGeneratedAt(filePath) {
    try {
        const artifact = readJsonFile(filePath);
        return normalizeText(artifact.generated_at);
    } catch {
        return null;
    }
}

function normalizeText(value) {
    const text = String(value ?? '').trim();
    return text || null;
}

function indexBy(items = [], keyName) {
    const output = new Map();
    for (const item of items) {
        const key = normalizeText(item?.[keyName]);
        if (key) output.set(key, item);
    }
    return output;
}

function countWhere(items = [], predicate) {
    return items.filter(predicate).length;
}

function isForbiddenSideEffectClear(value = {}) {
    return (
        value.live_fetch_performed === false &&
        value.detail_fetch_performed !== true &&
        value.network_request_performed === false &&
        value.db_write_performed === false &&
        value.raw_match_data_insert_performed === false &&
        value.raw_write_execution_performed === false
    );
}

function validateContext(context = {}) {
    const errors = [];
    if (context.azPlan?.proposal_phase !== 'Phase 5.21L2V3AZ') {
        errors.push('L2V3AZ suspended target review plan is required');
    }
    if (
        context.azPlan?.suspended_target_review_planning_status !==
        'completed_controlled_no_write_suspended_target_review_planning'
    ) {
        errors.push('L2V3AZ planning status must be completed');
    }
    if (
        context.azPlan?.planned_review_case_count !== 9 ||
        context.azPlan?.suspended_target_review_candidate_count !== 8
    ) {
        errors.push('L2V3AZ must plan 9 review cases for 8 suspended targets');
    }
    if (context.azPlan?.blocked_pending_review_target_count !== 42) {
        errors.push('L2V3AZ blocked_pending_review_target_count must be 42');
    }
    if (!isForbiddenSideEffectClear(context.azPlan)) {
        errors.push('L2V3AZ plan must remain no-fetch and no-write');
    }
    if (context.atSuspensionResult?.proposal_phase !== 'Phase 5.21L2V3AT') {
        errors.push('L2V3AT suspension result is required');
    }
    if (context.atSuspensionResult?.mapping_suspended_count !== 8) {
        errors.push('L2V3AT must record 8 suspended mappings');
    }
    if (context.atSuspensionResult?.blocked_pending_review_target_count !== 42) {
        errors.push('L2V3AT must keep 42 blocked_pending_review targets');
    }
    if (context.arContradictionResult?.proposal_phase !== 'Phase 5.21L2V3AR') {
        errors.push('L2V3AR contradiction review result is required');
    }
    if (context.arContradictionResult?.contradiction_confirmed_count !== 8) {
        errors.push('L2V3AR must confirm 8 reverse-fixture contradictions');
    }
    if (context.ayRegressionResult?.proposal_phase !== 'Phase 5.21L2V3AY') {
        errors.push('L2V3AY identity contract regression result is required');
    }
    if (
        context.ayRegressionResult?.executed_regression_case_count !== 7 ||
        context.ayRegressionResult?.failed_regression_case_count !== 0
    ) {
        errors.push('L2V3AY identity contract regression cases must all pass');
    }
    const manifestHasAzTail =
        context.manifest?.suspended_target_review_planning_status ===
            context.azPlan?.suspended_target_review_planning_status &&
        context.manifest?.recommended_next_step_after_l2v3az ===
            'Phase 5.21L2V3BA: controlled no-write suspended target review execution';
    const manifestHasAyAnchor =
        context.manifest?.recommended_next_step_after_l2v3ay ===
        'Phase 5.21L2V3AZ: controlled no-write suspended target review planning';
    if (!manifestHasAzTail && !manifestHasAyAnchor) {
        errors.push('proposal manifest must contain the L2V3AZ tail or the L2V3AY insertion anchor');
    }
    return errors;
}

function buildEvidenceSummary({ atTarget, arTarget, dateTarget, sourceRecord, isApTarget }) {
    const parts = [
        `current_effective_status=${atTarget?.current_effective_status || 'unknown'}`,
        `contradiction_review_status=${arTarget?.contradiction_review_status || 'unknown'}`,
        `date_rule_status=${dateTarget?.date_rule_status || 'unknown'}`,
        `identity_evidence_status=${sourceRecord?.identity_evidence_status || 'unknown'}`,
        'identity_contract_regression=passed',
        'page_url_base_alone_insufficient=true',
    ];
    if (isApTarget) {
        parts.push('runner_contract_followup_covered_by_l2v3aw_l2v3ay=true');
    }
    return parts.join('; ');
}

function buildSuspendedReviewCase(plannedCase = {}, maps = {}, context = {}) {
    const scheduleExternalId = normalizeText(plannedCase.schedule_external_id);
    const atTarget = maps.suspensionTargets.get(scheduleExternalId) || {};
    const arTarget = maps.contradictionTargets.get(scheduleExternalId) || {};
    const dateTarget = maps.dateTargets.get(scheduleExternalId) || {};
    const sourceRecord = maps.sourceRecords.get(plannedCase.match_id) || {};
    const isApTarget = scheduleExternalId === normalizeText(context.apBlockerInvestigation?.requested_external_id);
    const contradictionConfirmed =
        arTarget.contradiction_review_status === 'contradiction_confirmed' &&
        arTarget.accepted_mapping_contradiction_confirmed === true &&
        arTarget.baseline_acceptance_contradiction_confirmed === true;
    const reverseFixtureDetected = dateTarget.date_rule_status === 'reverse_fixture_detected';
    const currentlySuspended = atTarget.current_effective_status === 'suspended';
    const reviewDecision =
        contradictionConfirmed && reverseFixtureDetected && currentlySuspended
            ? 'remain_suspended'
            : 'requires_expanded_evidence';

    return {
        case_id: plannedCase.id,
        match_id: plannedCase.match_id,
        requested_external_id: scheduleExternalId,
        observed_external_id: normalizeText(plannedCase.observed_detail_external_id),
        input_artifacts_used: [
            'az_suspended_target_review_plan',
            'at_suspension_result',
            'ar_contradiction_review_result',
            'ay_identity_contract_regression_result',
            'y_source_inventory_acquisition_result',
            'n_expanded_date_rule_verification',
            ...(isApTarget ? ['ap_no_write_recapture_blocker_investigation'] : []),
        ],
        executed: true,
        review_decision: reviewDecision,
        evidence_summary: buildEvidenceSummary({ atTarget, arTarget, dateTarget, sourceRecord, isApTarget }),
        blocker_status:
            reviewDecision === 'remain_suspended'
                ? 'reverse_fixture_contradiction_confirmed_identity_contract_blocked'
                : 'expanded_evidence_required_before_any_re_acceptance_review',
        current_effective_status: atTarget.current_effective_status || 'unknown',
        contradiction_review_status: arTarget.contradiction_review_status || 'unknown',
        date_rule_status: dateTarget.date_rule_status || 'unknown',
        source_inventory_identity_evidence_status: sourceRecord.identity_evidence_status || 'unknown',
        identity_contract_regression_passed: true,
        page_url_base_alone_insufficient: true,
        re_acceptance_execution_performed: false,
        suspension_reversal_performed: false,
        rollback_execution_performed: false,
        raw_write_execution_ready: false,
        no_live_fetch: true,
        no_db_write: true,
        no_raw_write: true,
    };
}

function buildPoolControlCase(context = {}) {
    return {
        case_id: 'blocked_pending_review_pool_control',
        match_id: null,
        requested_external_id: null,
        observed_external_id: null,
        input_artifacts_used: [
            'az_suspended_target_review_plan',
            'at_suspension_result',
            'ar_contradiction_review_result',
            'y_source_inventory_acquisition_result',
            'v_source_inventory_enrichment_implementation',
        ],
        executed: true,
        review_decision: 'requires_expanded_evidence',
        evidence_summary:
            '42 blocked_pending_review targets remain blocked because reverse-fixture evidence is insufficient; they are not clean and cannot enter raw write eligibility.',
        blocker_status: 'expanded_reverse_fixture_evidence_review_required',
        blocked_pending_review_target_count: context.azPlan?.blocked_pending_review_target_count || 0,
        may_be_treated_as_clean: false,
        may_enter_raw_write_eligibility: false,
        re_acceptance_execution_performed: false,
        suspension_reversal_performed: false,
        rollback_execution_performed: false,
        raw_write_execution_ready: false,
        no_live_fetch: true,
        no_db_write: true,
        no_raw_write: true,
    };
}

function buildMaps(context = {}) {
    return {
        suspensionTargets: indexBy(context.atSuspensionResult?.suspended_targets || [], 'schedule_external_id'),
        contradictionTargets: indexBy(context.arContradictionResult?.review_targets || [], 'schedule_external_id'),
        dateTargets: indexBy(context.nDateRuleVerification?.target_summaries || [], 'schedule_external_id'),
        sourceRecords: indexBy(context.ySourceInventory?.source_inventory_metadata_records || [], 'match_id'),
    };
}

function buildArtifact(context = {}) {
    const validationErrors = validateContext(context);
    if (validationErrors.length > 0) {
        throw new Error(`Cannot execute L2V3BA suspended target review: ${validationErrors.join('; ')}`);
    }

    const maps = buildMaps(context);
    const suspendedCases = (context.azPlan.planned_review_cases || [])
        .filter(item => normalizeText(item.id)?.startsWith('suspended_target_review_'))
        .map(item => buildSuspendedReviewCase(item, maps, context));
    const reviewCases = [...suspendedCases, buildPoolControlCase(context)];
    const failedReviewCaseCount = countWhere(
        reviewCases,
        item => !ALLOWED_DECISIONS.includes(item.review_decision) || item.executed !== true
    );

    return {
        artifact_type: 'suspended_target_review_result',
        artifact_status: EXECUTION_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        generated_at: context.generatedAt,
        pr_type: 'data-artifact/review-execution',
        source_controlled_local_review_only: true,
        runtime_code_change_scope: 'local_no_write_review_helper_only',
        execution_status: EXECUTION_STATUS,
        suspended_target_review_execution_status: EXECUTION_STATUS,
        reviewed_input_artifact_count: REVIEWED_INPUTS.length,
        reviewed_input_artifact_paths: Object.fromEntries(REVIEWED_INPUTS),
        review_execution_performed: true,
        suspended_target_review_candidate_count: suspendedCases.length,
        pool_control_case_count: 1,
        executed_review_case_count: reviewCases.length,
        completed_review_case_count: reviewCases.length - failedReviewCaseCount,
        failed_review_case_count: failedReviewCaseCount,
        remain_suspended_count: countWhere(reviewCases, item => item.review_decision === 'remain_suspended'),
        eligible_for_re_acceptance_review_count: countWhere(
            reviewCases,
            item => item.review_decision === 'eligible_for_re_acceptance_review'
        ),
        requires_runner_contract_followup_count: countWhere(
            reviewCases,
            item => item.review_decision === 'requires_runner_contract_followup'
        ),
        requires_expanded_evidence_count: countWhere(
            reviewCases,
            item => item.review_decision === 'requires_expanded_evidence'
        ),
        reject_mapping_count: countWhere(reviewCases, item => item.review_decision === 'reject_mapping'),
        supersede_mapping_count: countWhere(reviewCases, item => item.review_decision === 'supersede_mapping'),
        blocked_pending_review_target_count: context.azPlan.blocked_pending_review_target_count,
        blocked_pending_review_target_status: 'blocked_pending_review_not_clean_not_raw_write_eligible',
        allowed_review_decisions: [...ALLOWED_DECISIONS],
        prohibited_review_decisions_absent: reviewCases.every(
            item => !PROHIBITED_DECISIONS.includes(item.review_decision)
        ),
        review_cases: reviewCases,
        raw_write_execution_ready: false,
        live_fetch_performed: false,
        detail_fetch_performed: false,
        network_request_performed: false,
        recapture_retry_performed: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        matches_write_performed: false,
        matches_external_id_modified: false,
        raw_write_execution_performed: false,
        raw_write_runner_write_mode_used: false,
        re_acceptance_execution_performed: false,
        suspension_reversal_performed: false,
        rollback_execution_performed: false,
        schema_migration_performed: false,
        parser_features_training_prediction_performed: false,
        full_payload_saved: false,
        full_payload_printed: false,
        full_source_body_saved: false,
        full_source_body_printed: false,
        large_artifact_added: false,
        full_phase_snapshot_added: false,
        recommended_next_step: NEXT_STEP,
        next_required_step: NEXT_REQUIRED_STEP,
    };
}

function buildReport(artifact = {}) {
    const lines = [
        '# Data Entrypoint Governance - Phase 5.21 L2V3BA',
        '',
        '## Scope',
        '',
        `- phase=${PHASE}`,
        `- phase_name=${PHASE_NAME}`,
        '- pr_type=data-artifact/review-execution',
        '- source_controlled_local_review_only=true',
        '- review_execution_performed=true',
        '- no live fetch',
        '- no detail fetch',
        '- no network request',
        '- no recapture retry',
        '- no DB writes',
        '- no raw_match_data inserts',
        '- no raw write execution',
        '- no re-acceptance execution',
        '- no suspension reversal',
        '- no rollback',
        '',
        '## Execution Summary',
        '',
        `- suspended_target_review_execution_status=${artifact.suspended_target_review_execution_status}`,
        `- suspended_target_review_candidate_count=${artifact.suspended_target_review_candidate_count}`,
        `- pool_control_case_count=${artifact.pool_control_case_count}`,
        `- executed_review_case_count=${artifact.executed_review_case_count}`,
        `- completed_review_case_count=${artifact.completed_review_case_count}`,
        `- failed_review_case_count=${artifact.failed_review_case_count}`,
        `- remain_suspended_count=${artifact.remain_suspended_count}`,
        `- eligible_for_re_acceptance_review_count=${artifact.eligible_for_re_acceptance_review_count}`,
        `- requires_runner_contract_followup_count=${artifact.requires_runner_contract_followup_count}`,
        `- requires_expanded_evidence_count=${artifact.requires_expanded_evidence_count}`,
        `- reject_mapping_count=${artifact.reject_mapping_count}`,
        `- supersede_mapping_count=${artifact.supersede_mapping_count}`,
        `- blocked_pending_review_target_count=${artifact.blocked_pending_review_target_count}`,
        '- raw_write_execution_ready=false',
        '',
        '## Review Case Results',
        '',
        ...artifact.review_cases.map(
            (item, index) =>
                `${index + 1}. ${item.case_id}: review_decision=${item.review_decision}; blocker_status=${item.blocker_status}`
        ),
        '',
        '## Blocked Pending Review Pool',
        '',
        '- The 42 blocked_pending_review targets remain blocked.',
        '- They are not clean and do not enter raw write eligibility.',
        '- Further work must be planning-only expanded review unless separately authorized.',
        '',
        '## Safety Result',
        '',
        '- live_fetch_performed=false',
        '- detail_fetch_performed=false',
        '- network_request_performed=false',
        '- recapture_retry_performed=false',
        '- db_write_performed=false',
        '- raw_match_data_insert_performed=false',
        '- raw_write_execution_performed=false',
        '- re_acceptance_execution_performed=false',
        '- suspension_reversal_performed=false',
        '- rollback_execution_performed=false',
        '',
        '## Artifact Guardrail Compliance',
        '',
        '- Added result manifest is a small review execution delta, not a full historical snapshot.',
        '- Added report is a concise governance summary.',
        '- Proposal manifest update records only the current BA result and next-step metadata.',
        '- No full raw_data, pageProps, body, or source body is saved or printed.',
        '',
        '## Next Step',
        '',
        `- recommended_next_step=${artifact.recommended_next_step}`,
    ];
    return `${lines.join('\n')}\n`;
}

function buildProposalManifestDeltaBlock(artifact = {}) {
    return [
        '    "phase_5_21_l2v3ba_execution_status": ' + JSON.stringify(artifact.execution_status) + ',',
        '    "phase_5_21_l2v3ba_artifact_path": ' + JSON.stringify(ARTIFACT_OUTPUT_PATH) + ',',
        '    "phase_5_21_l2v3ba_report_path": ' + JSON.stringify(REPORT_OUTPUT_PATH) + ',',
        '    "phase_5_21_l2v3ba_next_required_step": ' + JSON.stringify(artifact.next_required_step) + ',',
        '    "suspended_target_review_execution_status": ' +
            JSON.stringify(artifact.suspended_target_review_execution_status) +
            ',',
        '    "review_execution_performed": true,',
        `    "executed_review_case_count": ${artifact.executed_review_case_count},`,
        `    "completed_review_case_count": ${artifact.completed_review_case_count},`,
        `    "failed_review_case_count": ${artifact.failed_review_case_count},`,
        `    "pool_control_case_count": ${artifact.pool_control_case_count},`,
        `    "remain_suspended_count": ${artifact.remain_suspended_count},`,
        `    "eligible_for_re_acceptance_review_count": ${artifact.eligible_for_re_acceptance_review_count},`,
        `    "requires_runner_contract_followup_count": ${artifact.requires_runner_contract_followup_count},`,
        `    "requires_expanded_evidence_count": ${artifact.requires_expanded_evidence_count},`,
        `    "reject_mapping_count": ${artifact.reject_mapping_count},`,
        `    "supersede_mapping_count": ${artifact.supersede_mapping_count},`,
        '    "blocked_pending_review_target_status": ' +
            JSON.stringify(artifact.blocked_pending_review_target_status) +
            ',',
        '    "recommended_next_step_after_l2v3ba": ' + JSON.stringify(artifact.recommended_next_step),
    ].join('\n');
}

function buildAzProposalManifestDeltaBlock() {
    return [
        '    "phase_5_21_l2v3az_planning_status": "completed_controlled_no_write_suspended_target_review_planning",',
        '    "phase_5_21_l2v3az_artifact_path": ' + JSON.stringify(AZ_PLAN_PATH) + ',',
        '    "phase_5_21_l2v3az_report_path": ' +
            JSON.stringify('docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AZ.md') +
            ',',
        '    "phase_5_21_l2v3az_next_required_step": "controlled_no_write_suspended_target_review_execution",',
        '    "suspended_target_review_planning_status": "completed_controlled_no_write_suspended_target_review_planning",',
        '    "suspended_target_review_candidate_count": 8,',
        '    "planned_suspended_target_review_case_count": 9,',
        '    "planned_suspended_target_review_decision_count": 6,',
        '    "planned_suspended_target_review_blocking_rule_count": 7,',
        '    "recommended_next_step_after_l2v3az": "Phase 5.21L2V3BA: controlled no-write suspended target review execution"',
    ].join('\n');
}

function writeProposalManifestFile(filePath, artifact = {}) {
    const targetPath = absolutePath(filePath);
    const originalText = fs.readFileSync(targetPath, 'utf8');
    const deltaBlock = buildProposalManifestDeltaBlock(artifact);
    const replacement = `${PROPOSAL_INSERTION_ANCHOR},\n${deltaBlock}`;
    const fallbackReplacement = `${FALLBACK_PROPOSAL_INSERTION_ANCHOR},\n${buildAzProposalManifestDeltaBlock()},\n${deltaBlock}`;
    let nextText;

    if (originalText.includes('"phase_5_21_l2v3ba_execution_status"')) {
        const anchorWithComma = `${PROPOSAL_INSERTION_ANCHOR},`;
        const anchorStart = originalText.indexOf(anchorWithComma);
        const blockStart = originalText.indexOf('\n    "phase_5_21_l2v3ba_execution_status"', anchorStart);
        const blockEnd = originalText.lastIndexOf('\n}');
        if (anchorStart >= 0 && blockStart >= 0 && blockEnd > blockStart) {
            nextText = `${originalText.slice(0, anchorStart)}${replacement}${originalText.slice(blockEnd)}`;
        } else {
            nextText = originalText;
        }
    } else if (originalText.includes(PROPOSAL_INSERTION_ANCHOR)) {
        nextText = originalText.replace(PROPOSAL_INSERTION_ANCHOR, replacement);
    } else {
        nextText = originalText.replace(FALLBACK_PROPOSAL_INSERTION_ANCHOR, fallbackReplacement);
    }

    if (!nextText.includes('"phase_5_21_l2v3ba_execution_status"')) {
        throw new Error('Failed to apply minimal L2V3BA proposal manifest delta');
    }
    if (nextText === originalText) return;
    fs.writeFileSync(targetPath, nextText, 'utf8');
}

function loadContext(overrides = {}) {
    return {
        azPlan: overrides.azPlan || readJsonFile(AZ_PLAN_PATH),
        atSuspensionResult: overrides.atSuspensionResult || readJsonFile(AT_SUSPENSION_RESULT_PATH),
        arContradictionResult: overrides.arContradictionResult || readJsonFile(AR_CONTRADICTION_RESULT_PATH),
        ayRegressionResult: overrides.ayRegressionResult || readJsonFile(AY_REGRESSION_RESULT_PATH),
        apBlockerInvestigation: overrides.apBlockerInvestigation || readJsonFile(AP_BLOCKER_INVESTIGATION_PATH),
        ySourceInventory: overrides.ySourceInventory || readJsonFile(Y_SOURCE_INVENTORY_PATH),
        vSourceEnrichment: overrides.vSourceEnrichment || readJsonFile(V_SOURCE_ENRICHMENT_PATH),
        nDateRuleVerification: overrides.nDateRuleVerification || readJsonFile(N_DATE_RULE_VERIFICATION_PATH),
        manifest: overrides.manifest || readJsonFile(PROPOSAL_MANIFEST_PATH),
        generatedAt: overrides.generatedAt || readExistingGeneratedAt(ARTIFACT_OUTPUT_PATH) || new Date().toISOString(),
    };
}

function runSuspendedTargetReviewExecution(options = {}, overrides = {}) {
    const context = loadContext(overrides);
    const artifact = buildArtifact(context);
    const report = buildReport(artifact);
    const updatedManifest = { ...context.manifest };

    for (const [key, value] of Object.entries({
        phase_5_21_l2v3ba_execution_status: artifact.execution_status,
        phase_5_21_l2v3ba_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3ba_report_path: REPORT_OUTPUT_PATH,
        phase_5_21_l2v3ba_next_required_step: artifact.next_required_step,
        suspended_target_review_execution_status: artifact.suspended_target_review_execution_status,
        review_execution_performed: true,
        executed_review_case_count: artifact.executed_review_case_count,
        completed_review_case_count: artifact.completed_review_case_count,
        failed_review_case_count: artifact.failed_review_case_count,
        pool_control_case_count: artifact.pool_control_case_count,
        remain_suspended_count: artifact.remain_suspended_count,
        eligible_for_re_acceptance_review_count: artifact.eligible_for_re_acceptance_review_count,
        requires_runner_contract_followup_count: artifact.requires_runner_contract_followup_count,
        requires_expanded_evidence_count: artifact.requires_expanded_evidence_count,
        reject_mapping_count: artifact.reject_mapping_count,
        supersede_mapping_count: artifact.supersede_mapping_count,
        blocked_pending_review_target_status: artifact.blocked_pending_review_target_status,
        recommended_next_step_after_l2v3ba: artifact.recommended_next_step,
    })) {
        updatedManifest[key] = value;
    }

    if (options.writeFiles !== false) {
        const jsonWriter = overrides.writeJsonFile || writeJsonFile;
        const textWriter = overrides.writeTextFile || writeTextFile;
        const proposalWriter = overrides.writeProposalManifestFile || writeProposalManifestFile;
        jsonWriter(ARTIFACT_OUTPUT_PATH, artifact);
        textWriter(REPORT_OUTPUT_PATH, report);
        proposalWriter(PROPOSAL_MANIFEST_PATH, artifact);
    }

    return {
        ok: true,
        artifact,
        report,
        updated_manifest: updatedManifest,
    };
}

function runCli() {
    const result = runSuspendedTargetReviewExecution();
    process.stdout.write(
        `${JSON.stringify({
            ok: result.ok,
            phase: PHASE,
            suspended_target_review_execution_status: result.artifact.suspended_target_review_execution_status,
            executed_review_case_count: result.artifact.executed_review_case_count,
            completed_review_case_count: result.artifact.completed_review_case_count,
            failed_review_case_count: result.artifact.failed_review_case_count,
            remain_suspended_count: result.artifact.remain_suspended_count,
            requires_expanded_evidence_count: result.artifact.requires_expanded_evidence_count,
            raw_write_execution_ready: result.artifact.raw_write_execution_ready,
            live_fetch_performed: result.artifact.live_fetch_performed,
            network_request_performed: result.artifact.network_request_performed,
            db_write_performed: result.artifact.db_write_performed,
            recommended_next_step: result.artifact.recommended_next_step,
        })}\n`
    );
}

if (require.main === module) {
    runCli();
}

module.exports = {
    PHASE,
    EXECUTION_STATUS,
    NEXT_STEP,
    PROPOSAL_MANIFEST_PATH,
    AZ_PLAN_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_OUTPUT_PATH,
    PROPOSAL_INSERTION_ANCHOR,
    ALLOWED_DECISIONS,
    PROHIBITED_DECISIONS,
    buildArtifact,
    buildReport,
    buildProposalManifestDeltaBlock,
    writeProposalManifestFile,
    loadContext,
    runSuspendedTargetReviewExecution,
    runCli,
};
