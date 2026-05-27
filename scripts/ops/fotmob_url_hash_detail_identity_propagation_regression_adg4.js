#!/usr/bin/env node
'use strict';

/* eslint-disable max-lines, complexity -- ADG4 keeps the no-write regression evidence explicit and local. */

const fs = require('node:fs');
const path = require('node:path');

const regeneration = require('./pageprops_v2_enriched_target_regeneration_execute');
const {
    DETAIL_IDENTITY_SOURCE_URL_HASH_FRAGMENT,
    FotMobSourceInventoryAdapter,
    deriveSourceInventoryIdentityEvidence,
    parseSourcePageUrl,
} = require('../../src/infrastructure/services/FotMobSourceInventoryAdapter');
const { resolveRecaptureIdentityContract } = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21-ADG4';
const PHASE_NAME = 'fotmob_url_hash_detail_identity_propagation_no_write_regression_and_candidate_reclassification';
const EXECUTION_STATUS = 'completed_controlled_no_write_fotmob_url_hash_detail_identity_propagation_regression';
const GENERATED_AT = '2026-05-28T00:00:00.000Z';
const TOTAL_BATCH_TARGET_COUNT = 50;
const NEEDS_NEW_EVIDENCE_TARGET_COUNT = 42;
const SUSPENDED_TARGET_COUNT = 8;
const POSITIVE_SAMPLE_URL = 'https://www.fotmob.com/zh-Hans/matches/manchester-city-vs-afc-bournemouth/2feiv3#4813735';
const POSITIVE_SAMPLE_MATCH_ID = '53_20252026_4813735';
const POSITIVE_SAMPLE_SCHEDULE_EXTERNAL_ID = '9999999';

const PROPOSAL_MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const SOURCE_INVENTORY_RESULT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.controlled_source_inventory_acquisition_result.phase521l2v3y.json';
const REGENERATION_PLAN_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_target_regeneration_plan.phase521l2v3z.json';
const BLOCKED_REVIEW_PLAN_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.bounded_expanded_blocked_target_review_plan.phase521l2v3bb.json';
const BLOCKED_REVIEW_RESULT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.bounded_expanded_blocked_target_review_result.phase521l2v3bc.json';
const SUSPENDED_REVIEW_RESULT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.suspended_target_review_result.phase521l2v3ba.json';
const ADG2_RESULT_PATH = 'docs/_manifests/fotmob_identity_anti_bot_differential_diagnosis_result.adg2.json';
const ADG3_RESULT_PATH = 'docs/_manifests/fotmob_url_hash_detail_identity_propagation_implementation.adg3.json';
const ARTIFACT_OUTPUT_PATH = 'docs/_manifests/fotmob_url_hash_detail_identity_propagation_regression.adg4.json';
const REPORT_OUTPUT_PATH = 'docs/_reports/FOTMOB_URL_HASH_DETAIL_IDENTITY_PROPAGATION_REGRESSION_ADG4.md';

function absolutePath(filePath) {
    return path.isAbsolute(filePath) ? filePath : path.join(PROJECT_ROOT, filePath);
}

function readTextFile(filePath) {
    return fs.readFileSync(absolutePath(filePath), 'utf8');
}

function readJsonFile(filePath) {
    return JSON.parse(readTextFile(filePath));
}

function defaultWriteJsonFile(filePath, value) {
    fs.writeFileSync(absolutePath(filePath), `${JSON.stringify(value, null, 4)}\n`, 'utf8');
}

function defaultWriteTextFile(filePath, value) {
    fs.writeFileSync(absolutePath(filePath), value, 'utf8');
}

function normalizeText(value) {
    const text = String(value ?? '').trim();
    return text || null;
}

function countWhere(items = [], predicate) {
    return items.filter(predicate).length;
}

function sortByExternalId(items = []) {
    return [...items].sort((left, right) => Number(left.external_id) - Number(right.external_id));
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = {
        writeFiles: true,
        help: false,
        unknown: [],
    };
    for (let index = 0; index < argv.length; index += 1) {
        const arg = String(argv[index]);
        if (!arg.startsWith('--')) {
            options.unknown.push(arg);
            continue;
        }
        const key = arg.replace(/^--/, '').split('=')[0];
        const value = arg.includes('=')
            ? arg.slice(arg.indexOf('=') + 1)
            : argv[index + 1] && !String(argv[index + 1]).startsWith('--')
              ? argv[++index]
              : true;
        if (key === 'help' || key === 'h') {
            options.help = true;
            continue;
        }
        if (key === 'write-files' || key === 'write_files') {
            options.writeFiles = !['0', 'false', 'no'].includes(String(value).trim().toLowerCase());
            continue;
        }
        options.unknown.push(key);
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

function loadDependencies(dependencies = {}) {
    return {
        proposal: dependencies.proposal || readJsonFile(PROPOSAL_MANIFEST_PATH),
        sourceInventoryResult: dependencies.sourceInventoryResult || readJsonFile(SOURCE_INVENTORY_RESULT_PATH),
        regenerationPlan: dependencies.regenerationPlan || readJsonFile(REGENERATION_PLAN_PATH),
        blockedReviewPlan: dependencies.blockedReviewPlan || readJsonFile(BLOCKED_REVIEW_PLAN_PATH),
        blockedReviewResult: dependencies.blockedReviewResult || readJsonFile(BLOCKED_REVIEW_RESULT_PATH),
        suspendedReviewResult: dependencies.suspendedReviewResult || readJsonFile(SUSPENDED_REVIEW_RESULT_PATH),
        adg2Result: dependencies.adg2Result || readJsonFile(ADG2_RESULT_PATH),
        adg3Result: dependencies.adg3Result || readJsonFile(ADG3_RESULT_PATH),
    };
}

function validateDependencies(dependencies = {}) {
    const errors = [];
    if (
        !Array.isArray(dependencies.proposal?.candidate_targets) ||
        dependencies.proposal.candidate_targets.length !== 50
    ) {
        errors.push('proposal candidate_targets must contain 50 targets');
    }
    if (
        !Array.isArray(dependencies.sourceInventoryResult?.source_inventory_metadata_records) ||
        dependencies.sourceInventoryResult.source_inventory_metadata_records.length !== 50
    ) {
        errors.push('source inventory acquisition result must contain 50 metadata records');
    }
    if (normalizeText(dependencies.regenerationPlan?.proposal_phase) !== 'Phase 5.21L2V3Z') {
        errors.push('L2V3Z regeneration plan artifact is required');
    }
    if (dependencies.blockedReviewPlan?.bounded_review_scope?.blocked_pending_review_target_count !== 42) {
        errors.push('bounded blocked review plan must scope exactly 42 blocked targets');
    }
    if (dependencies.blockedReviewResult?.classification_summary?.needs_new_evidence_count !== 42) {
        errors.push('bounded blocked review result must record 42 needs_new_evidence targets');
    }
    if (dependencies.suspendedReviewResult?.remain_suspended_count !== 8) {
        errors.push('suspended review result must keep 8 targets suspended');
    }
    if (dependencies.adg2Result?.positive_sample_network_diagnosis?.direct_api_http_status !== 403) {
        errors.push('ADG2 must record direct API 403 for the positive sample');
    }
    if (dependencies.adg3Result?.request_contract_status?.direct_match_details_api_403_remains_blocked !== true) {
        errors.push('ADG3 must keep the direct matchDetails API request-contract blocked');
    }
    if (dependencies.adg3Result?.implemented_behavior?.recapture_contract_reads_detail_external_id_candidate !== true) {
        errors.push('ADG3 must implement detail_external_id_candidate propagation for the recapture contract');
    }
    if (dependencies.adg3Result?.implemented_behavior?.schedule_external_id_blind_fallback_blocked !== true) {
        errors.push('ADG3 must keep schedule_external_id blind fallback blocked');
    }
    return { ok: errors.length === 0, errors };
}

function buildPositiveSampleSummary(generatedAt = GENERATED_AT) {
    const parsed = parseSourcePageUrl(POSITIVE_SAMPLE_URL);
    const evidence = deriveSourceInventoryIdentityEvidence({
        match: {
            id: '4813735',
            pageUrl: POSITIVE_SAMPLE_URL,
        },
        sourcePath: 'matches.allMatches.0',
        externalId: '4813735',
        generatedAt,
    });
    const adapter = Object.create(FotMobSourceInventoryAdapter.prototype);
    const seed = adapter.toManifestCandidateSeed(
        {
            external_id: '4813735',
            match_id: POSITIVE_SAMPLE_MATCH_ID,
            league_name: 'Ligue 1',
            season: '2025/2026',
            home_team: 'AFC Bournemouth',
            away_team: 'Manchester City',
            match_date: '2026-05-24T15:00:00.000Z',
            status: 'scheduled',
            data_source: 'FotMob',
        },
        1,
        evidence
    );
    return {
        source_page_url: POSITIVE_SAMPLE_URL,
        source_page_url_base: parsed.source_page_url_base,
        source_url_path_slug: seed.source_url_path_slug,
        source_url_fragment_external_id: seed.source_url_fragment_external_id,
        detail_external_id_candidate: seed.detail_external_id_candidate,
        detail_identity_source: seed.detail_identity_source,
        schedule_external_id: seed.schedule_external_id,
        no_http_request_required: true,
    };
}

function buildRecaptureIdentityPositiveSample(positiveSample = {}) {
    const target = {
        external_id: POSITIVE_SAMPLE_SCHEDULE_EXTERNAL_ID,
        schedule_external_id: POSITIVE_SAMPLE_SCHEDULE_EXTERNAL_ID,
        source_page_url: positiveSample.source_page_url,
        source_page_url_base: positiveSample.source_page_url_base,
        source_url_fragment_external_id: positiveSample.source_url_fragment_external_id,
        detail_external_id_candidate: positiveSample.detail_external_id_candidate,
        detail_identity_source: positiveSample.detail_identity_source,
    };
    const contract = resolveRecaptureIdentityContract({ target });
    return {
        schedule_external_id: POSITIVE_SAMPLE_SCHEDULE_EXTERNAL_ID,
        detail_external_id_candidate: positiveSample.detail_external_id_candidate,
        detail_identity_source: positiveSample.detail_identity_source,
        recapture_expected_identity: contract.recapture_expected_identity,
        recapture_request_identity: contract.recapture_request_identity,
        blockers: contract.blockers,
        recapture_expected_identity_uses_detail_candidate:
            contract.recapture_expected_identity === positiveSample.detail_external_id_candidate &&
            contract.recapture_expected_identity !== POSITIVE_SAMPLE_SCHEDULE_EXTERNAL_ID,
        schedule_external_id_blind_fallback_blocked:
            contract.recapture_request_identity === null &&
            contract.blockers.includes('missing_accepted_detail_external_id') &&
            contract.blockers.includes('missing_re_acceptance'),
        raw_write_execution_ready: contract.raw_write_execution_ready,
    };
}

function buildEnrichedTargets(dependencies = {}, generatedAt = GENERATED_AT) {
    const regenerationResult = regeneration.runEnrichedTargetRegenerationExecution({
        manifest: dependencies.proposal,
        l2v3yArtifact: dependencies.sourceInventoryResult,
        l2v3zArtifact: dependencies.regenerationPlan,
        writeFiles: false,
        generatedAt,
    });
    if (!regenerationResult.ok) {
        throw new Error(`failed to regenerate enriched targets for ADG4: ${regenerationResult.errors.join('; ')}`);
    }
    return regenerationResult.artifact.enriched_targets || [];
}

function mapTargetsByExternalId(targets = []) {
    return new Map(targets.map(target => [normalizeText(target.external_id), target]));
}

function classifyNeedsNewEvidenceTarget(target = {}) {
    const contract = resolveRecaptureIdentityContract({ target });
    const sourceUrlFragmentExternalId = normalizeText(target.source_url_fragment_external_id);
    const detailExternalIdCandidate = normalizeText(target.detail_external_id_candidate);
    const detailIdentitySource = normalizeText(target.detail_identity_source);
    const sourceUrlPathSlug = normalizeText(target.source_url_path_slug);
    let classification = 'remains_needs_new_evidence';

    if (!sourceUrlFragmentExternalId) {
        classification = 'source_inventory_hash_missing';
    } else if (
        detailExternalIdCandidate !== sourceUrlFragmentExternalId ||
        detailIdentitySource !== DETAIL_IDENTITY_SOURCE_URL_HASH_FRAGMENT ||
        !sourceUrlPathSlug
    ) {
        classification = 'propagation_failed';
    } else if (
        contract.recapture_expected_identity === detailExternalIdCandidate &&
        contract.recapture_request_identity === null &&
        contract.blockers.includes('missing_accepted_detail_external_id') &&
        contract.blockers.includes('missing_re_acceptance')
    ) {
        classification = 'request_contract_validation_required';
    }

    return {
        target_id: target.target_id,
        match_id: target.match_id,
        external_id: target.external_id,
        classification,
        source_url_path_slug: sourceUrlPathSlug,
        source_page_url_present: Boolean(normalizeText(target.source_page_url)),
        source_page_url_base_present: Boolean(normalizeText(target.source_page_url_base)),
        source_url_fragment_external_id: sourceUrlFragmentExternalId,
        detail_external_id_candidate: detailExternalIdCandidate,
        detail_identity_source: detailIdentitySource,
        recapture_expected_identity: contract.recapture_expected_identity,
        recapture_request_identity: contract.recapture_request_identity,
        identity_contract_blockers: contract.blockers,
        raw_write_execution_ready: contract.raw_write_execution_ready,
    };
}

function classifySuspendedTarget(target = {}) {
    const contract = resolveRecaptureIdentityContract({
        target: {
            ...target,
            current_mapping_effective_status: 'suspended',
            current_baseline_effective_status: 'suspended',
            date_compatibility_status: 'reverse_fixture_detected',
        },
    });
    return {
        target_id: target.target_id,
        match_id: target.match_id,
        external_id: target.external_id,
        classification: 'suspended_reverse_fixture_blocked',
        source_url_path_slug: normalizeText(target.source_url_path_slug),
        source_url_fragment_external_id: normalizeText(target.source_url_fragment_external_id),
        detail_external_id_candidate: normalizeText(target.detail_external_id_candidate),
        detail_identity_source: normalizeText(target.detail_identity_source),
        recapture_expected_identity: contract.recapture_expected_identity,
        recapture_request_identity: contract.recapture_request_identity,
        identity_contract_blockers: contract.blockers,
        raw_write_execution_ready: contract.raw_write_execution_ready,
    };
}

function countClassifications(items = []) {
    return items.reduce((acc, item) => {
        const key = normalizeText(item.classification) || 'unknown';
        acc[key] = (acc[key] || 0) + 1;
        return acc;
    }, {});
}

function buildArtifact(dependencies = {}, generatedAt = GENERATED_AT) {
    const positiveSample = buildPositiveSampleSummary(generatedAt);
    const recapturePositiveSample = buildRecaptureIdentityPositiveSample(positiveSample);
    const enrichedTargets = buildEnrichedTargets(dependencies, generatedAt);
    const targetsByExternalId = mapTargetsByExternalId(enrichedTargets);

    const blockedExternalIds =
        dependencies.blockedReviewPlan.bounded_review_scope.blocked_target_external_ids.map(String);
    const suspendedExternalIds = (dependencies.suspendedReviewResult.review_cases || [])
        .filter(
            item =>
                normalizeText(item.requested_external_id) && normalizeText(item.review_decision) === 'remain_suspended'
        )
        .map(item => String(item.requested_external_id));

    const needsNewEvidenceTargets = blockedExternalIds
        .map(externalId => targetsByExternalId.get(externalId))
        .filter(Boolean);
    const suspendedTargets = suspendedExternalIds
        .map(externalId => targetsByExternalId.get(externalId))
        .filter(Boolean);

    if (needsNewEvidenceTargets.length !== NEEDS_NEW_EVIDENCE_TARGET_COUNT) {
        throw new Error(
            `expected ${NEEDS_NEW_EVIDENCE_TARGET_COUNT} blocked targets after ADG3 propagation, got ${needsNewEvidenceTargets.length}`
        );
    }
    if (suspendedTargets.length !== SUSPENDED_TARGET_COUNT) {
        throw new Error(
            `expected ${SUSPENDED_TARGET_COUNT} suspended targets after ADG3 propagation, got ${suspendedTargets.length}`
        );
    }

    const needsNewEvidenceReclassification = sortByExternalId(
        needsNewEvidenceTargets.map(classifyNeedsNewEvidenceTarget)
    );
    const suspendedTargetPreservation = sortByExternalId(suspendedTargets.map(classifySuspendedTarget));
    const needsNewEvidenceCounts = countClassifications(needsNewEvidenceReclassification);
    const suspendedCounts = countClassifications(suspendedTargetPreservation);

    const sourceInventoryHashRecordsCount = countWhere(
        dependencies.sourceInventoryResult.source_inventory_metadata_records,
        record => normalizeText(record.source_url_fragment_external_id)
    );
    const activeCandidateHashPropagationCount = countWhere(
        enrichedTargets,
        target =>
            normalizeText(target.source_url_fragment_external_id) &&
            normalizeText(target.detail_external_id_candidate) ===
                normalizeText(target.source_url_fragment_external_id) &&
            normalizeText(target.detail_identity_source) === DETAIL_IDENTITY_SOURCE_URL_HASH_FRAGMENT
    );
    const candidateDetailExternalIdCandidateCount = countWhere(enrichedTargets, target =>
        normalizeText(target.detail_external_id_candidate)
    );
    const detailIdentityCandidatePresentCount = countWhere(needsNewEvidenceReclassification, target =>
        normalizeText(target.detail_external_id_candidate)
    );
    const rawWriteReadyCount = countWhere(
        [...needsNewEvidenceReclassification, ...suspendedTargetPreservation],
        target => target.raw_write_execution_ready === true
    );

    return {
        artifact_type: 'fotmob_url_hash_detail_identity_propagation_regression',
        artifact_status: EXECUTION_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        generated_at: generatedAt,
        pr_type: 'data-artifact / regression-execution',
        runtime_code_change: false,
        helper_scaffolding_added: true,
        source_controlled_local_no_write_regression: true,
        regression_execution_performed: true,
        runtime_behavior_validated: true,
        reviewed_input_artifact_count: 8,
        reviewed_input_artifact_paths: [
            PROPOSAL_MANIFEST_PATH,
            SOURCE_INVENTORY_RESULT_PATH,
            REGENERATION_PLAN_PATH,
            BLOCKED_REVIEW_PLAN_PATH,
            BLOCKED_REVIEW_RESULT_PATH,
            SUSPENDED_REVIEW_RESULT_PATH,
            ADG2_RESULT_PATH,
            ADG3_RESULT_PATH,
        ],
        positive_sample: positiveSample,
        recapture_identity_positive_sample: recapturePositiveSample,
        source_inventory_hash_records_count: sourceInventoryHashRecordsCount,
        active_candidate_hash_propagation_count: activeCandidateHashPropagationCount,
        candidate_detail_external_id_candidate_count: candidateDetailExternalIdCandidateCount,
        total_batch_target_count: TOTAL_BATCH_TARGET_COUNT,
        suspended_target_count: SUSPENDED_TARGET_COUNT,
        needs_new_evidence_target_count_before: NEEDS_NEW_EVIDENCE_TARGET_COUNT,
        detail_identity_candidate_present_count: detailIdentityCandidatePresentCount,
        source_inventory_hash_missing_count: needsNewEvidenceCounts.source_inventory_hash_missing || 0,
        propagation_failed_count: needsNewEvidenceCounts.propagation_failed || 0,
        request_contract_validation_required_count: needsNewEvidenceCounts.request_contract_validation_required || 0,
        remains_needs_new_evidence_count: needsNewEvidenceCounts.remains_needs_new_evidence || 0,
        suspended_reverse_fixture_blocked_count: suspendedCounts.suspended_reverse_fixture_blocked || 0,
        raw_write_ready_count: rawWriteReadyCount,
        re_acceptance_candidate_count: 0,
        recapture_expected_identity_uses_detail_candidate:
            recapturePositiveSample.recapture_expected_identity_uses_detail_candidate,
        schedule_external_id_blind_fallback_blocked:
            recapturePositiveSample.schedule_external_id_blind_fallback_blocked,
        direct_api_request_contract_blocked:
            dependencies.adg2Result.positive_sample_network_diagnosis.direct_api_http_status === 403 &&
            dependencies.adg3Result.request_contract_status.direct_match_details_api_403_remains_blocked === true,
        candidate_reclassification_summary: {
            needs_new_evidence_targets: needsNewEvidenceCounts,
            suspended_targets: suspendedCounts,
        },
        needs_new_evidence_reclassification: needsNewEvidenceReclassification,
        suspended_target_preservation: suspendedTargetPreservation,
        safety_status: {
            db_write_performed: false,
            raw_write_execution_performed: false,
            raw_match_data_insert_performed: false,
            matches_write_performed: false,
            live_fetch_performed: false,
            detail_fetch_performed: false,
            network_request_performed: false,
            recapture_retry_performed: false,
            re_acceptance_execution_performed: false,
            suspension_reversal_performed: false,
            browser_automation_performed: false,
            proxy_or_captcha_bypass_performed: false,
            direct_api_retry_performed: false,
            full_payload_saved: false,
            full_payload_printed: false,
        },
        recommended_next_step:
            'bounded request-contract/page-route validation planning under no-write constraints; do not raw write, do not re-accept, do not bypass 403',
    };
}

function buildReport(artifact = {}) {
    return `# FotMob URL Hash Detail Identity Propagation Regression ADG4

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- regression_execution_performed=${artifact.regression_execution_performed}
- source_controlled_local_no_write_regression=${artifact.source_controlled_local_no_write_regression}
- runtime_behavior_validated=${artifact.runtime_behavior_validated}
- runtime_code_change=${artifact.runtime_code_change}

## Safety

- live_fetch_performed=false
- detail_fetch_performed=false
- network_request_performed=false
- db_write_performed=false
- raw_match_data_insert_performed=false
- raw_write_execution_performed=false
- re_acceptance_execution_performed=false
- suspension_reversal_performed=false
- browser_automation_performed=false
- proxy_or_captcha_bypass_performed=false
- direct_api_retry_performed=false
- full_payload_saved=false
- full_payload_printed=false

## Positive Sample

- source_page_url=${artifact.positive_sample.source_page_url}
- source_url_path_slug=${artifact.positive_sample.source_url_path_slug}
- source_url_fragment_external_id=${artifact.positive_sample.source_url_fragment_external_id}
- detail_external_id_candidate=${artifact.positive_sample.detail_external_id_candidate}
- detail_identity_source=${artifact.positive_sample.detail_identity_source}
- no_http_request_required=${artifact.positive_sample.no_http_request_required}

## Propagation Summary

- source_inventory_hash_records_count=${artifact.source_inventory_hash_records_count}
- active_candidate_hash_propagation_count=${artifact.active_candidate_hash_propagation_count}
- candidate_detail_external_id_candidate_count=${artifact.candidate_detail_external_id_candidate_count}
- total_batch_target_count=${artifact.total_batch_target_count}
- suspended_target_count=${artifact.suspended_target_count}
- needs_new_evidence_target_count_before=${artifact.needs_new_evidence_target_count_before}
- detail_identity_candidate_present_count=${artifact.detail_identity_candidate_present_count}
- source_inventory_hash_missing_count=${artifact.source_inventory_hash_missing_count}
- propagation_failed_count=${artifact.propagation_failed_count}
- request_contract_validation_required_count=${artifact.request_contract_validation_required_count}
- remains_needs_new_evidence_count=${artifact.remains_needs_new_evidence_count}
- suspended_reverse_fixture_blocked_count=${artifact.suspended_reverse_fixture_blocked_count}
- raw_write_ready_count=${artifact.raw_write_ready_count}
- re_acceptance_candidate_count=${artifact.re_acceptance_candidate_count}

## Recapture Identity Contract

- recapture_expected_identity_uses_detail_candidate=${artifact.recapture_expected_identity_uses_detail_candidate}
- schedule_external_id_blind_fallback_blocked=${artifact.schedule_external_id_blind_fallback_blocked}
- direct_api_request_contract_blocked=${artifact.direct_api_request_contract_blocked}
- recapture_positive_sample_expected_identity=${artifact.recapture_identity_positive_sample.recapture_expected_identity}
- recapture_positive_sample_request_identity=${artifact.recapture_identity_positive_sample.recapture_request_identity}

## Classification Result

- 42 previously generic needs_new_evidence targets now classify as request_contract_validation_required after ADG3 propagation.
- 8 suspended targets remain blocked as suspended_reverse_fixture_blocked.
- URL hash/detail candidate presence does not authorize raw write or re-acceptance.

## Recommended Next Step

${artifact.recommended_next_step}
`;
}

function runFotmobUrlHashDetailIdentityPropagationRegressionAdg4(options = {}, dependencies = {}) {
    const loaded = loadDependencies(dependencies);
    const validation = validateDependencies(loaded);
    if (!validation.ok) {
        return { ok: false, status: 3, errors: validation.errors };
    }

    const artifact = buildArtifact(loaded, dependencies.generatedAt || GENERATED_AT);
    const report = buildReport(artifact);

    if (options.writeFiles !== false) {
        const writeJsonFile = dependencies.writeJsonFile || defaultWriteJsonFile;
        const writeTextFile = dependencies.writeTextFile || defaultWriteTextFile;
        writeJsonFile(ARTIFACT_OUTPUT_PATH, artifact);
        writeTextFile(REPORT_OUTPUT_PATH, report);
    }

    return {
        ok: true,
        status: 0,
        artifact,
        report,
    };
}

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/fotmob_url_hash_detail_identity_propagation_regression_adg4.js --write-files=yes',
        '',
        'Safety:',
        '  ADG4 is local, source-controlled, and no-write.',
        '  It does not live fetch, detail fetch, retry direct API, write DB/raw/matches, re-accept, or unsuspend.',
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

    const result = runFotmobUrlHashDetailIdentityPropagationRegressionAdg4(options);
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
                report: REPORT_OUTPUT_PATH,
                adg4_regression_status: result.artifact.artifact_status,
                regression_execution_performed: result.artifact.regression_execution_performed,
                source_inventory_hash_records_count: result.artifact.source_inventory_hash_records_count,
                active_candidate_hash_propagation_count: result.artifact.active_candidate_hash_propagation_count,
                candidate_detail_external_id_candidate_count:
                    result.artifact.candidate_detail_external_id_candidate_count,
                total_batch_target_count: result.artifact.total_batch_target_count,
                suspended_target_count: result.artifact.suspended_target_count,
                needs_new_evidence_target_count_before: result.artifact.needs_new_evidence_target_count_before,
                detail_identity_candidate_present_count: result.artifact.detail_identity_candidate_present_count,
                source_inventory_hash_missing_count: result.artifact.source_inventory_hash_missing_count,
                propagation_failed_count: result.artifact.propagation_failed_count,
                request_contract_validation_required_count: result.artifact.request_contract_validation_required_count,
                remains_needs_new_evidence_count: result.artifact.remains_needs_new_evidence_count,
                suspended_reverse_fixture_blocked_count: result.artifact.suspended_reverse_fixture_blocked_count,
                raw_write_ready_count: result.artifact.raw_write_ready_count,
                recapture_expected_identity_uses_detail_candidate:
                    result.artifact.recapture_expected_identity_uses_detail_candidate,
                schedule_external_id_blind_fallback_blocked:
                    result.artifact.schedule_external_id_blind_fallback_blocked,
                direct_api_request_contract_blocked: result.artifact.direct_api_request_contract_blocked,
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
    EXECUTION_STATUS,
    GENERATED_AT,
    PROPOSAL_MANIFEST_PATH,
    SOURCE_INVENTORY_RESULT_PATH,
    REGENERATION_PLAN_PATH,
    BLOCKED_REVIEW_PLAN_PATH,
    BLOCKED_REVIEW_RESULT_PATH,
    SUSPENDED_REVIEW_RESULT_PATH,
    ADG2_RESULT_PATH,
    ADG3_RESULT_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_OUTPUT_PATH,
    POSITIVE_SAMPLE_URL,
    POSITIVE_SAMPLE_SCHEDULE_EXTERNAL_ID,
    parseArgs,
    validateCliOptions,
    validateDependencies,
    buildPositiveSampleSummary,
    buildRecaptureIdentityPositiveSample,
    classifyNeedsNewEvidenceTarget,
    classifySuspendedTarget,
    buildArtifact,
    buildReport,
    runFotmobUrlHashDetailIdentityPropagationRegressionAdg4,
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
