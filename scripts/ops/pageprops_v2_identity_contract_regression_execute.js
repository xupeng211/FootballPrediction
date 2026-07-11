#!/usr/bin/env node
'use strict';

/* eslint-disable max-lines, complexity -- L2V3AY keeps no-write regression evidence explicit for review. */

const fs = require('node:fs');
const path = require('node:path');

const recapture = require('./pageprops_v2_no_write_payload_recapture_execute');
const { resolveRecaptureIdentityContract } = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3AY';
const PHASE_NAME = 'controlled_no_write_identity_contract_regression_execution';
const EXECUTION_STATUS = 'completed_controlled_no_write_identity_contract_regression_execution';
const BLOCKED_STATUS = 'blocked_controlled_no_write_identity_contract_regression_execution';
const AX_EXECUTION_NEXT_STEP = 'Phase 5.21L2V3AY: controlled no-write identity contract regression execution';
const NEXT_STEP = 'Phase 5.21L2V3AZ: controlled no-write suspended target review planning';
const NEXT_REQUIRED_STEP = 'controlled_no_write_suspended_target_review_planning';
const PROPOSAL_MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const AX_PLAN_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.identity_contract_regression_plan.phase521l2v3ax.json';
const AW_IMPLEMENTATION_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.recapture_runner_identity_input_contract_fix_implementation.phase521l2v3aw.json';
const AO_RECAPTURE_RESULT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.no_write_payload_recapture_result.phase521l2v3ao.json';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.identity_contract_regression_result.phase521l2v3ay.json';
const REPORT_OUTPUT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AY.md';
const BASE_TARGET_EXTERNAL_ID = '4830466';
const OBSERVED_MISMATCH_EXTERNAL_ID = '4830759';
const PROPOSAL_INSERTION_ANCHOR =
    '    "recommended_next_step_after_l2v3ax": "Phase 5.21L2V3AY: controlled no-write identity contract regression execution"';
const REVIEWED_INPUTS = Object.freeze([
    ['ax_regression_plan_manifest', AX_PLAN_PATH],
    ['ax_regression_plan_report', 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AX.md'],
    ['aw_implementation_manifest', AW_IMPLEMENTATION_PATH],
    ['aw_implementation_report', 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AW.md'],
    ['ao_no_write_recapture_result', AO_RECAPTURE_RESULT_PATH],
    [
        'aw_implementation_tests',
        'tests/unit/pageprops_v2_recapture_runner_identity_input_contract_fix_implementation_aw.test.js',
    ],
    ['recapture_runner', 'scripts/ops/pageprops_v2_no_write_payload_recapture_execute.js'],
    ['route_identity_reconciler', 'src/infrastructure/services/FotMobRouteIdentityReconciler.js'],
    ['proposal_manifest', PROPOSAL_MANIFEST_PATH],
]);
const BLOCKING_RULES = Object.freeze([
    ['schedule_external_id_default_detail_route_blocked', 'schedule_external_id_is_correlation_only'],
    ['suspended_mapping_or_baseline_blocks_recapture', 'suspended_mapping_baseline_blocks_before_fetch'],
    ['missing_re_acceptance_blocks_recapture', 'missing_re_acceptance_blocks_before_fetch'],
    ['page_url_base_slug_fragment_alone_insufficient', 'page_url_base_slug_fragment_alone_insufficient'],
    ['identity_mismatch_blocks_recapture', 'requested_4830466_observed_4830759_remains_blocked'],
    [
        'hash_mismatch_secondary_to_identity_mismatch_blocks_baseline_update',
        'hash_mismatch_under_identity_mismatch_cannot_update_baseline',
    ],
    ['raw_write_execution_ready_false_until_future_authorization', 'raw_write_execution_ready_remains_false'],
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

function buildProposalManifestDeltaBlock(artifact = {}) {
    return [
        '    "phase_5_21_l2v3ay_execution_status": ' + JSON.stringify(artifact.execution_status) + ',',
        '    "phase_5_21_l2v3ay_artifact_path": ' + JSON.stringify(ARTIFACT_OUTPUT_PATH) + ',',
        '    "phase_5_21_l2v3ay_report_path": ' + JSON.stringify(REPORT_OUTPUT_PATH) + ',',
        '    "phase_5_21_l2v3ay_next_required_step": ' + JSON.stringify(artifact.next_required_step) + ',',
        '    "identity_contract_regression_execution_status": ' +
            JSON.stringify(artifact.regression_execution_status) +
            ',',
        '    "identity_contract_regression_execution_performed": true,',
        `    "executed_regression_case_count": ${artifact.executed_regression_case_count},`,
        `    "passed_regression_case_count": ${artifact.passed_regression_case_count},`,
        `    "failed_regression_case_count": ${artifact.failed_regression_case_count},`,
        `    "blocking_rule_verified_count": ${artifact.blocking_rule_verified_count},`,
        `    "schedule_side_route_default_block_verified": ${artifact.schedule_side_route_default_block_verified},`,
        `    "suspended_mapping_baseline_block_verified": ${artifact.suspended_mapping_baseline_block_verified},`,
        `    "missing_re_acceptance_block_verified": ${artifact.missing_re_acceptance_block_verified},`,
        `    "page_url_base_alone_insufficient_verified": ${artifact.page_url_base_alone_insufficient_verified},`,
        `    "requested_observed_mismatch_block_verified": ${artifact.requested_observed_mismatch_block_verified},`,
        '    "hash_mismatch_under_identity_mismatch_baseline_update_block_verified": ' +
            `${artifact.hash_mismatch_under_identity_mismatch_baseline_update_block_verified},`,
        '    "recommended_next_step_after_l2v3ay": ' + JSON.stringify(artifact.recommended_next_step),
    ].join('\n');
}

function writeProposalManifestFile(filePath, artifact = {}) {
    const targetPath = absolutePath(filePath);
    const originalText = fs.readFileSync(targetPath, 'utf8');
    const deltaBlock = buildProposalManifestDeltaBlock(artifact);
    const replacement = `${PROPOSAL_INSERTION_ANCHOR},\n${deltaBlock}`;
    let nextText;

    if (originalText.includes('"phase_5_21_l2v3ay_execution_status"')) {
        const anchorWithComma = `${PROPOSAL_INSERTION_ANCHOR},`;
        const anchorStart = originalText.indexOf(anchorWithComma);
        const blockStart = originalText.indexOf('\n    "phase_5_21_l2v3ay_execution_status"', anchorStart);
        const blockEnd = originalText.lastIndexOf('\n}');
        if (anchorStart >= 0 && blockStart >= 0 && blockEnd > blockStart) {
            nextText = `${originalText.slice(0, anchorStart)}${replacement}${originalText.slice(blockEnd)}`;
        } else {
            nextText = originalText;
        }
    } else {
        nextText = originalText.replace(PROPOSAL_INSERTION_ANCHOR, replacement);
    }

    if (!nextText.includes('"phase_5_21_l2v3ay_execution_status"')) {
        throw new Error('Failed to apply minimal L2V3AY proposal manifest delta');
    }
    if (nextText === originalText) return;
    fs.writeFileSync(targetPath, nextText, 'utf8');
}

function normalizeText(value) {
    const text = String(value ?? '').trim();
    return text || null;
}

function normalizeLower(value) {
    return String(value ?? '')
        .trim()
        .toLowerCase();
}

function safeBoolean(value, fallback = false) {
    return typeof value === 'boolean' ? value : fallback;
}

function firstNonEmpty(...values) {
    for (const value of values) {
        const text = normalizeText(value);
        if (text) return text;
    }
    return null;
}

function cloneJson(value) {
    return value === undefined ? undefined : JSON.parse(JSON.stringify(value));
}

function mergeObjects(baseValue = {}, overrideValue = {}) {
    const base = cloneJson(baseValue);
    const override = cloneJson(overrideValue);
    if (!isPlainObject(base) || !isPlainObject(override)) return override;
    const output = { ...base };
    for (const [key, value] of Object.entries(override)) {
        if (isPlainObject(value) && isPlainObject(output[key])) {
            output[key] = mergeObjects(output[key], value);
            continue;
        }
        output[key] = cloneJson(value);
    }
    return output;
}

function isPlainObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function findBaseTarget(manifest = {}) {
    const targets = Array.isArray(manifest.candidate_targets) ? manifest.candidate_targets : [];
    return (
        targets.find(target => normalizeText(target.external_id) === BASE_TARGET_EXTERNAL_ID) ||
        targets.find(target => normalizeText(target.match_id) === `53_20252026_${BASE_TARGET_EXTERNAL_ID}`) ||
        null
    );
}

function validateContext(context = {}) {
    const errors = [];
    if (normalizeText(context.axPlan?.proposal_phase) !== 'Phase 5.21L2V3AX') {
        errors.push('L2V3AX plan artifact is required');
    }
    if (
        normalizeText(context.axPlan?.regression_planning_status) !==
        'completed_controlled_no_write_identity_contract_regression_planning'
    ) {
        errors.push('L2V3AX regression planning status must be completed');
    }
    if (Number(context.axPlan?.planned_regression_case_count) !== 7) {
        errors.push('L2V3AX planned_regression_case_count must be 7');
    }
    if (Number(context.axPlan?.planned_blocking_rule_count) !== 7) {
        errors.push('L2V3AX planned_blocking_rule_count must be 7');
    }
    if (context.axPlan?.live_fetch_performed !== false || context.axPlan?.network_request_performed !== false) {
        errors.push('L2V3AX must remain no-live-fetch and no-network');
    }
    if (
        context.axPlan?.db_write_performed !== false ||
        context.axPlan?.raw_match_data_insert_performed !== false ||
        context.axPlan?.raw_write_execution_performed !== false
    ) {
        errors.push('L2V3AX must remain no-write');
    }
    if (normalizeText(context.awImplementation?.proposal_phase) !== 'Phase 5.21L2V3AW') {
        errors.push('L2V3AW implementation artifact is required');
    }
    if (
        normalizeText(context.awImplementation?.artifact_status) !==
        'completed_recapture_runner_identity_input_contract_fix_implementation'
    ) {
        errors.push('L2V3AW implementation artifact must be completed');
    }
    if (context.awImplementation?.raw_write_execution_ready !== false) {
        errors.push('L2V3AW must keep raw_write_execution_ready=false');
    }
    if (normalizeText(context.aoResult?.proposal_phase) !== 'Phase 5.21L2V3AO') {
        errors.push('L2V3AO result artifact is required');
    }
    if (context.aoResult?.raw_write_execution_ready !== false) {
        errors.push('L2V3AO must keep raw_write_execution_ready=false');
    }
    if (
        normalizeText(context.manifest?.phase_5_21_l2v3ax_planning_status) !==
        'completed_controlled_no_write_identity_contract_regression_planning'
    ) {
        errors.push('proposal manifest must record completed L2V3AX planning status');
    }
    if (normalizeText(context.manifest?.recommended_next_step_after_l2v3ax) !== AX_EXECUTION_NEXT_STEP) {
        errors.push('proposal manifest must point from L2V3AX to L2V3AY');
    }
    if (!context.baseTarget) {
        errors.push(`proposal manifest target ${BASE_TARGET_EXTERNAL_ID} is required`);
    }
    if (!/^[a-f0-9]{64}$/.test(normalizeLower(context.baseTarget?.baseline_hash))) {
        errors.push(`proposal manifest target ${BASE_TARGET_EXTERNAL_ID} baseline_hash must be 64 lowercase hex`);
    }
    return errors;
}

function buildFixturePageProps(detailExternalId = OBSERVED_MISMATCH_EXTERNAL_ID, overrides = {}) {
    return mergeObjects(
        {
            content: { stats: [] },
            general: {
                matchId: detailExternalId,
                homeTeam: { name: 'Rennes' },
                awayTeam: { name: 'Marseille' },
                matchTimeUTC: '2026-05-17T19:00:00.000Z',
                status: 'finished',
                pageUrl: `/match/${detailExternalId}`,
            },
            header: {
                teams: [{ name: 'Rennes' }, { name: 'Marseille' }],
                status: { utcTime: '2026-05-17T19:00:00.000Z' },
            },
        },
        overrides
    );
}

function buildFixtureHtml(pageProps = {}) {
    return `<html><head><script id="__NEXT_DATA__" type="application/json">${JSON.stringify({
        props: { pageProps },
    })}</script></head><body>fixture</body></html>`;
}

function buildFetchResult(requestUrl, pageProps = {}, finalUrl = requestUrl) {
    const body = buildFixtureHtml(pageProps);
    return {
        ok: true,
        request_url: requestUrl,
        final_url: finalUrl,
        http_status: 200,
        body_byte_length: Buffer.byteLength(body, 'utf8'),
        body,
    };
}

function ensureHashMismatch(baselineHash, observedHash) {
    const normalizedBaseline = normalizeLower(baselineHash);
    const normalizedObserved = normalizeLower(observedHash);
    if (normalizedBaseline && normalizedBaseline !== normalizedObserved) return normalizedBaseline;
    const firstChar = normalizedObserved[0] === '0' ? '1' : '0';
    return `${firstChar}${normalizedObserved.slice(1)}`;
}

function buildCaseTarget(baseTarget = {}, overrides = {}) {
    return {
        target_id: normalizeText(baseTarget.target_id),
        match_id: normalizeText(baseTarget.match_id),
        external_id: normalizeText(baseTarget.external_id),
        schedule_external_id: firstNonEmpty(baseTarget.schedule_external_id, baseTarget.external_id),
        source_page_url: normalizeText(baseTarget.source_page_url),
        source_page_url_base: normalizeText(baseTarget.source_page_url_base),
        source_url_fragment_external_id: normalizeText(baseTarget.source_url_fragment_external_id),
        accepted_detail_external_id: normalizeText(baseTarget.accepted_detail_external_id),
        current_mapping_effective_status: normalizeText(baseTarget.current_mapping_effective_status),
        current_baseline_effective_status: normalizeText(baseTarget.current_baseline_effective_status),
        re_acceptance_execution_performed: safeBoolean(baseTarget.re_acceptance_execution_performed, false),
        home_team: firstNonEmpty(baseTarget.home_team, baseTarget.schedule_home_team),
        away_team: firstNonEmpty(baseTarget.away_team, baseTarget.schedule_away_team),
        kickoff_time: firstNonEmpty(baseTarget.kickoff_time, baseTarget.match_date, baseTarget.schedule_date),
        match_date: firstNonEmpty(baseTarget.match_date, baseTarget.kickoff_time, baseTarget.schedule_date),
        status: firstNonEmpty(baseTarget.status, 'finished'),
        baseline_hash: normalizeLower(baseTarget.baseline_hash),
        ...cloneJson(overrides),
    };
}

function buildCaseRecord({
    caseId,
    inputSource,
    expectedBehavior,
    pass,
    observedBehavior,
    verifiedBlockers = [],
    rawWriteExecutionReady = false,
}) {
    return {
        case_id: caseId,
        input_source: inputSource,
        executed: true,
        result: pass ? 'pass' : 'fail',
        expected_behavior: expectedBehavior,
        observed_behavior: observedBehavior,
        blocker_status: pass ? 'verified' : 'failed',
        verified_blockers: verifiedBlockers,
        no_live_fetch: true,
        no_detail_fetch: true,
        no_network_request: true,
        no_db_write: true,
        no_raw_write: true,
        raw_write_execution_ready: rawWriteExecutionReady === true,
    };
}

function buildBlockingRuleRecords(caseResults = []) {
    const caseById = new Map(caseResults.map(item => [item.case_id, item]));
    return BLOCKING_RULES.map(([ruleId, caseId]) => {
        const caseResult = caseById.get(caseId);
        return {
            rule_id: ruleId,
            covered_by_case_id: caseId,
            verified: caseResult?.result === 'pass',
        };
    });
}

async function executeRegressionCases(context = {}) {
    const baseTarget = buildCaseTarget(context.baseTarget);
    const inputSourceBase = `${PROPOSAL_MANIFEST_PATH}:candidate_target:${baseTarget.match_id}`;
    const mismatchPageProps = buildFixturePageProps();
    const mismatchPagePropsHash = recapture.computeStablePagePropsHash(mismatchPageProps);
    const mismatchBaselineHash = ensureHashMismatch(baseTarget.baseline_hash, mismatchPagePropsHash);

    const case1Target = buildCaseTarget(baseTarget, {
        source_page_url_base: `/match/${BASE_TARGET_EXTERNAL_ID}`,
        source_url_fragment_external_id: BASE_TARGET_EXTERNAL_ID,
    });
    const case1Contract = resolveRecaptureIdentityContract({ target: case1Target });
    const case1Pass =
        case1Contract.recapture_request_allowed === false &&
        case1Contract.recapture_request_identity === null &&
        case1Contract.schedule_external_id === BASE_TARGET_EXTERNAL_ID &&
        case1Contract.route_identity_strategy === 'blocked_until_reaccepted_identity_contract' &&
        case1Contract.canonical_identity_source === 'none_until_reaccepted_mapping_baseline' &&
        Array.isArray(case1Contract.blockers) &&
        case1Contract.blockers.includes('missing_accepted_detail_external_id');

    let case2FetchCalled = false;
    const case2Target = buildCaseTarget(baseTarget, {
        accepted_detail_external_id: OBSERVED_MISMATCH_EXTERNAL_ID,
        current_mapping_effective_status: 'suspended',
        current_baseline_effective_status: 'suspended',
        re_acceptance_execution_performed: true,
        source_page_url: `/match/${OBSERVED_MISMATCH_EXTERNAL_ID}#${OBSERVED_MISMATCH_EXTERNAL_ID}`,
        source_page_url_base: `/match/${OBSERVED_MISMATCH_EXTERNAL_ID}`,
        source_url_fragment_external_id: OBSERVED_MISMATCH_EXTERNAL_ID,
    });
    const case2Runtime = await recapture.recaptureTarget(
        case2Target,
        0,
        { timeoutMs: 1000 },
        {
            fetchHtmlFn: async () => {
                case2FetchCalled = true;
                throw new Error('fetch must not be called');
            },
        }
    );
    const case2Pass =
        case2FetchCalled === false &&
        case2Runtime.identity_contract_blocked === true &&
        case2Runtime.stopping_rule_triggered === 'identity_contract_blocked' &&
        Array.isArray(case2Runtime.blocker_list) &&
        case2Runtime.blocker_list.includes('suspended_mapping_or_baseline') &&
        case2Runtime.recapture_request_identity === null;

    const case3Target = buildCaseTarget(baseTarget, {
        accepted_detail_external_id: OBSERVED_MISMATCH_EXTERNAL_ID,
        current_mapping_effective_status: 'accepted',
        current_baseline_effective_status: 'accepted',
        re_acceptance_execution_performed: false,
        source_page_url: `/match/${OBSERVED_MISMATCH_EXTERNAL_ID}#${OBSERVED_MISMATCH_EXTERNAL_ID}`,
        source_page_url_base: `/match/${OBSERVED_MISMATCH_EXTERNAL_ID}`,
        source_url_fragment_external_id: OBSERVED_MISMATCH_EXTERNAL_ID,
    });
    const case3Contract = resolveRecaptureIdentityContract({ target: case3Target });
    const case3Pass =
        case3Contract.recapture_request_allowed === false &&
        case3Contract.recapture_request_identity === null &&
        Array.isArray(case3Contract.blockers) &&
        case3Contract.blockers.includes('missing_re_acceptance') &&
        case3Contract.recapture_request_identity !== case3Target.schedule_external_id;

    const case4Target = buildCaseTarget(baseTarget, {
        source_page_url: '/matches/rennes-vs-marseille/2t9n7h#4830466',
        source_page_url_base: '/matches/rennes-vs-marseille/2t9n7h',
        source_url_fragment_external_id: BASE_TARGET_EXTERNAL_ID,
        current_mapping_effective_status: 'accepted',
        current_baseline_effective_status: 'accepted',
        re_acceptance_execution_performed: false,
    });
    const case4Contract = resolveRecaptureIdentityContract({ target: case4Target });
    const case4Pass =
        case4Contract.recapture_request_allowed === false &&
        case4Contract.page_url_base_alone_insufficient_enforced === true &&
        Array.isArray(case4Contract.blockers) &&
        case4Contract.blockers.includes('page_url_base_alone_insufficient') &&
        case4Contract.raw_write_execution_ready === false;

    const case5Target = buildCaseTarget(baseTarget, {
        accepted_detail_external_id: BASE_TARGET_EXTERNAL_ID,
        current_mapping_effective_status: 'reaccepted',
        current_baseline_effective_status: 'reaccepted',
        re_acceptance_execution_performed: true,
        source_page_url: `/match/${BASE_TARGET_EXTERNAL_ID}#${BASE_TARGET_EXTERNAL_ID}`,
        source_page_url_base: `/match/${BASE_TARGET_EXTERNAL_ID}`,
        source_url_fragment_external_id: BASE_TARGET_EXTERNAL_ID,
        baseline_hash: mismatchBaselineHash,
    });
    const case5Runtime = await recapture.recaptureTarget(
        case5Target,
        0,
        { timeoutMs: 1000 },
        {
            fetchHtmlFn: async requestUrl =>
                buildFetchResult(
                    requestUrl,
                    mismatchPageProps,
                    `https://www.fotmob.com/match/${OBSERVED_MISMATCH_EXTERNAL_ID}`
                ),
        }
    );
    const case5Pass =
        case5Runtime.target_status === 'blocked' &&
        case5Runtime.stopping_rule_triggered === 'identity_mismatch' &&
        case5Runtime.recapture_request_identity === BASE_TARGET_EXTERNAL_ID &&
        case5Runtime.observed_detail_external_id === OBSERVED_MISMATCH_EXTERNAL_ID &&
        case5Runtime.identity_match_status === 'mismatch';

    const case6Pass =
        case5Runtime.hash_validation_status === 'secondary_to_identity_mismatch' &&
        Array.isArray(case5Runtime.blocker_list) &&
        case5Runtime.blocker_list.includes('hash_mismatch_secondary_to_identity_mismatch') &&
        case5Runtime.hash_matches_baseline === false &&
        case5Runtime.baseline_update_allowed === false;

    const rawWriteReadyValues = [
        case1Contract.raw_write_execution_ready,
        case2Runtime.raw_write_execution_ready,
        case3Contract.raw_write_execution_ready,
        case4Contract.raw_write_execution_ready,
        case5Runtime.raw_write_execution_ready,
    ];
    const case7Pass = rawWriteReadyValues.every(value => value === false);

    const caseResults = [
        buildCaseRecord({
            caseId: 'schedule_external_id_is_correlation_only',
            inputSource: `${inputSourceBase} + local_in_memory_identity_input`,
            expectedBehavior: 'schedule-side external_id is not blindly used as detail route identity',
            pass: case1Pass,
            observedBehavior: {
                recapture_request_allowed: case1Contract.recapture_request_allowed,
                recapture_request_identity: case1Contract.recapture_request_identity,
                route_identity_strategy: case1Contract.route_identity_strategy,
                canonical_identity_source: case1Contract.canonical_identity_source,
            },
            verifiedBlockers: case1Contract.blockers || [],
            rawWriteExecutionReady: case1Contract.raw_write_execution_ready,
        }),
        buildCaseRecord({
            caseId: 'suspended_mapping_baseline_blocks_before_fetch',
            inputSource: `${inputSourceBase} + local_in_memory_suspended_target`,
            expectedBehavior: 'suspended mapping or baseline blocks recapture before fetch',
            pass: case2Pass,
            observedBehavior: {
                fetch_called: case2FetchCalled,
                identity_contract_blocked: case2Runtime.identity_contract_blocked,
                stopping_rule_triggered: case2Runtime.stopping_rule_triggered,
                recapture_request_identity: case2Runtime.recapture_request_identity,
            },
            verifiedBlockers: case2Runtime.blocker_list || [],
            rawWriteExecutionReady: case2Runtime.raw_write_execution_ready,
        }),
        buildCaseRecord({
            caseId: 'missing_re_acceptance_blocks_before_fetch',
            inputSource: `${inputSourceBase} + local_in_memory_missing_re_acceptance_target`,
            expectedBehavior: 'missing re-acceptance blocks recapture before fetch',
            pass: case3Pass,
            observedBehavior: {
                recapture_request_allowed: case3Contract.recapture_request_allowed,
                recapture_request_identity: case3Contract.recapture_request_identity,
                route_identity_strategy: case3Contract.route_identity_strategy,
            },
            verifiedBlockers: case3Contract.blockers || [],
            rawWriteExecutionReady: case3Contract.raw_write_execution_ready,
        }),
        buildCaseRecord({
            caseId: 'page_url_base_slug_fragment_alone_insufficient',
            inputSource: `${inputSourceBase} + local_in_memory_page_url_evidence_fixture`,
            expectedBehavior: 'page_url_base, slug, and fragment evidence alone remain insufficient',
            pass: case4Pass,
            observedBehavior: {
                recapture_request_allowed: case4Contract.recapture_request_allowed,
                page_url_base_alone_insufficient_enforced: case4Contract.page_url_base_alone_insufficient_enforced,
                route_identity_strategy: case4Contract.route_identity_strategy,
            },
            verifiedBlockers: case4Contract.blockers || [],
            rawWriteExecutionReady: case4Contract.raw_write_execution_ready,
        }),
        buildCaseRecord({
            caseId: 'requested_4830466_observed_4830759_remains_blocked',
            inputSource: `${inputSourceBase} + local_in_memory_pageprops_fixture`,
            expectedBehavior: 'requested 4830466 observed 4830759 remains blocked',
            pass: case5Pass,
            observedBehavior: {
                recapture_request_identity: case5Runtime.recapture_request_identity,
                observed_detail_external_id: case5Runtime.observed_detail_external_id,
                identity_match_status: case5Runtime.identity_match_status,
                stopping_rule_triggered: case5Runtime.stopping_rule_triggered,
            },
            verifiedBlockers: case5Runtime.blocker_list || [],
            rawWriteExecutionReady: case5Runtime.raw_write_execution_ready,
        }),
        buildCaseRecord({
            caseId: 'hash_mismatch_under_identity_mismatch_cannot_update_baseline',
            inputSource: `${inputSourceBase} + local_in_memory_pageprops_fixture`,
            expectedBehavior: 'hash mismatch under identity mismatch cannot update baseline',
            pass: case6Pass,
            observedBehavior: {
                hash_validation_status: case5Runtime.hash_validation_status,
                hash_matches_baseline: case5Runtime.hash_matches_baseline,
                baseline_update_allowed: case5Runtime.baseline_update_allowed,
            },
            verifiedBlockers: case5Runtime.blocker_list || [],
            rawWriteExecutionReady: case5Runtime.raw_write_execution_ready,
        }),
        buildCaseRecord({
            caseId: 'raw_write_execution_ready_remains_false',
            inputSource: `${inputSourceBase} + aggregate_case_results`,
            expectedBehavior: 'raw_write_execution_ready remains false',
            pass: case7Pass,
            observedBehavior: {
                raw_write_execution_ready_values: rawWriteReadyValues,
                all_cases_false: case7Pass,
            },
            verifiedBlockers: ['raw_write_execution_ready_false_until_future_authorization'],
            rawWriteExecutionReady: false,
        }),
    ];

    return {
        caseResults,
        mismatchPagePropsHash,
        mismatchBaselineHash,
    };
}

async function buildArtifact(context = {}) {
    const validationErrors = validateContext(context);
    if (validationErrors.length > 0) {
        throw new Error(`Cannot execute ${PHASE}: ${validationErrors.join('; ')}`);
    }

    const execution = await executeRegressionCases(context);
    const caseResults = execution.caseResults;
    const passedCount = caseResults.filter(item => item.result === 'pass').length;
    const failedCount = caseResults.length - passedCount;
    const blockingRules = buildBlockingRuleRecords(caseResults);
    const blockingRuleVerifiedCount = blockingRules.filter(item => item.verified).length;
    const executionStatus = failedCount === 0 ? EXECUTION_STATUS : BLOCKED_STATUS;

    return {
        artifact_type: 'identity_contract_regression_result',
        artifact_status: executionStatus,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        generated_at: context.generatedAt,
        execution_status: executionStatus,
        regression_execution_status: executionStatus,
        regression_execution_performed: true,
        reviewed_input_artifact_count: REVIEWED_INPUTS.length,
        reviewed_input_artifact_paths: Object.fromEntries(REVIEWED_INPUTS),
        planning_source_phase: 'Phase 5.21L2V3AX',
        case_target_id: context.baseTarget.target_id,
        case_match_id: context.baseTarget.match_id,
        case_schedule_external_id: firstNonEmpty(
            context.baseTarget.schedule_external_id,
            context.baseTarget.external_id
        ),
        case_observed_mismatch_external_id: OBSERVED_MISMATCH_EXTERNAL_ID,
        planned_regression_case_count: 7,
        executed_regression_case_count: caseResults.length,
        passed_regression_case_count: passedCount,
        failed_regression_case_count: failedCount,
        planned_blocking_rule_count: 7,
        blocking_rule_verified_count: blockingRuleVerifiedCount,
        schedule_side_route_default_block_verified:
            caseResults.find(item => item.case_id === 'schedule_external_id_is_correlation_only')?.result === 'pass',
        suspended_mapping_baseline_block_verified:
            caseResults.find(item => item.case_id === 'suspended_mapping_baseline_blocks_before_fetch')?.result ===
            'pass',
        missing_re_acceptance_block_verified:
            caseResults.find(item => item.case_id === 'missing_re_acceptance_blocks_before_fetch')?.result === 'pass',
        page_url_base_alone_insufficient_verified:
            caseResults.find(item => item.case_id === 'page_url_base_slug_fragment_alone_insufficient')?.result ===
            'pass',
        requested_observed_mismatch_block_verified:
            caseResults.find(item => item.case_id === 'requested_4830466_observed_4830759_remains_blocked')?.result ===
            'pass',
        hash_mismatch_under_identity_mismatch_baseline_update_block_verified:
            caseResults.find(item => item.case_id === 'hash_mismatch_under_identity_mismatch_cannot_update_baseline')
                ?.result === 'pass',
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
        re_acceptance_execution_performed: false,
        suspension_reversal_performed: false,
        rollback_execution_performed: false,
        parser_features_training_prediction_performed: false,
        schema_migration_performed: false,
        full_payload_saved: false,
        full_payload_printed: false,
        full_source_body_saved: false,
        full_source_body_printed: false,
        recommended_next_step: NEXT_STEP,
        next_required_step: NEXT_REQUIRED_STEP,
        regression_cases: caseResults,
        blocking_rules: blockingRules,
    };
}

function buildReport(artifact = {}) {
    const caseRows = (artifact.regression_cases || [])
        .map(item => {
            const blockerText = (item.verified_blockers || []).join(',') || 'none';
            return [
                `1. ${item.case_id}`,
                `    - result=${item.result}`,
                `    - expected_behavior=${item.expected_behavior}`,
                `    - blocker_status=${item.blocker_status}`,
                `    - verified_blockers=${blockerText}`,
                `    - no_live_fetch=${item.no_live_fetch}`,
                `    - no_db_write=${item.no_db_write}`,
                `    - no_raw_write=${item.no_raw_write}`,
            ].join('\n');
        })
        .join('\n');
    const blockingRuleRows = (artifact.blocking_rules || [])
        .map(rule => `- ${rule.rule_id}: verified=${rule.verified} covered_by_case_id=${rule.covered_by_case_id}`)
        .join('\n');

    return `# Data Entrypoint Governance - Phase 5.21 L2V3AY

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- regression_execution_performed=true
- source_controlled_local_only=true
- no live fetch
- no detail fetch
- no network request
- no recapture retry
- no DB writes
- no raw_match_data inserts
- no matches writes
- no matches.external_id changes
- no raw write execution
- no re-acceptance execution
- no suspension reversal
- no rollback

## Regression Execution Summary

- regression_execution_status=${artifact.regression_execution_status}
- planned_regression_case_count=${artifact.planned_regression_case_count}
- executed_regression_case_count=${artifact.executed_regression_case_count}
- passed_regression_case_count=${artifact.passed_regression_case_count}
- failed_regression_case_count=${artifact.failed_regression_case_count}
- planned_blocking_rule_count=${artifact.planned_blocking_rule_count}
- blocking_rule_verified_count=${artifact.blocking_rule_verified_count}
- schedule_side_route_default_block_verified=${artifact.schedule_side_route_default_block_verified}
- suspended_mapping_baseline_block_verified=${artifact.suspended_mapping_baseline_block_verified}
- missing_re_acceptance_block_verified=${artifact.missing_re_acceptance_block_verified}
- page_url_base_alone_insufficient_verified=${artifact.page_url_base_alone_insufficient_verified}
- requested_observed_mismatch_block_verified=${artifact.requested_observed_mismatch_block_verified}
- hash_mismatch_under_identity_mismatch_baseline_update_block_verified=${artifact.hash_mismatch_under_identity_mismatch_baseline_update_block_verified}
- raw_write_execution_ready=${artifact.raw_write_execution_ready}

## Regression Cases

${caseRows}

## Blocking Rules

${blockingRuleRows}

## Safety Result

- live_fetch_performed=${artifact.live_fetch_performed}
- detail_fetch_performed=${artifact.detail_fetch_performed}
- network_request_performed=${artifact.network_request_performed}
- recapture_retry_performed=${artifact.recapture_retry_performed}
- db_write_performed=${artifact.db_write_performed}
- raw_match_data_insert_performed=${artifact.raw_match_data_insert_performed}
- matches_write_performed=${artifact.matches_write_performed}
- matches_external_id_modified=${artifact.matches_external_id_modified}
- raw_write_execution_performed=${artifact.raw_write_execution_performed}
- re_acceptance_execution_performed=${artifact.re_acceptance_execution_performed}
- suspension_reversal_performed=${artifact.suspension_reversal_performed}
- rollback_execution_performed=${artifact.rollback_execution_performed}
- parser_features_training_prediction_performed=${artifact.parser_features_training_prediction_performed}
- schema_migration_performed=${artifact.schema_migration_performed}
- full_payload_saved=${artifact.full_payload_saved}
- full_payload_printed=${artifact.full_payload_printed}

## Artifact Guardrail Compliance

- result manifest records only the 7 regression cases and 7 blocking rules.
- report is a small execution delta, not a full historical snapshot.
- proposal manifest update is limited to current-state execution status and next-step metadata.
- no large artifact, no full payload, no archive cleanup, no history deletion.

## Next Step

- recommended_next_step=${artifact.recommended_next_step}
`;
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    return {
        ...manifest,
        phase_5_21_l2v3ay_execution_status: artifact.execution_status,
        phase_5_21_l2v3ay_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3ay_report_path: REPORT_OUTPUT_PATH,
        phase_5_21_l2v3ay_next_required_step: artifact.next_required_step,
        identity_contract_regression_execution_status: artifact.regression_execution_status,
        identity_contract_regression_execution_performed: true,
        executed_regression_case_count: artifact.executed_regression_case_count,
        passed_regression_case_count: artifact.passed_regression_case_count,
        failed_regression_case_count: artifact.failed_regression_case_count,
        blocking_rule_verified_count: artifact.blocking_rule_verified_count,
        schedule_side_route_default_block_verified: artifact.schedule_side_route_default_block_verified,
        suspended_mapping_baseline_block_verified: artifact.suspended_mapping_baseline_block_verified,
        missing_re_acceptance_block_verified: artifact.missing_re_acceptance_block_verified,
        page_url_base_alone_insufficient_verified: artifact.page_url_base_alone_insufficient_verified,
        requested_observed_mismatch_block_verified: artifact.requested_observed_mismatch_block_verified,
        hash_mismatch_under_identity_mismatch_baseline_update_block_verified:
            artifact.hash_mismatch_under_identity_mismatch_baseline_update_block_verified,
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
        re_acceptance_execution_performed: false,
        suspension_reversal_performed: false,
        rollback_execution_performed: false,
        recommended_next_step_after_l2v3ay: artifact.recommended_next_step,
    };
}

function loadContext(overrides = {}) {
    const readJson = overrides.readJsonFile || readJsonFile;
    const manifest = overrides.manifest || readJson(PROPOSAL_MANIFEST_PATH);
    return {
        manifest,
        axPlan: overrides.axPlan || readJson(AX_PLAN_PATH),
        awImplementation: overrides.awImplementation || readJson(AW_IMPLEMENTATION_PATH),
        aoResult: overrides.aoResult || readJson(AO_RECAPTURE_RESULT_PATH),
        baseTarget: overrides.baseTarget || findBaseTarget(manifest),
        generatedAt: overrides.generatedAt || new Date().toISOString(),
        writeJsonFile: overrides.writeJsonFile || writeJsonFile,
        writeTextFile: overrides.writeTextFile || writeTextFile,
        writeProposalManifestFile: overrides.writeProposalManifestFile || writeProposalManifestFile,
    };
}

async function runIdentityContractRegressionExecution(options = {}, overrides = {}) {
    const context = loadContext(overrides);
    const artifact = await buildArtifact(context);
    const report = buildReport(artifact);
    const updatedManifest = updateManifestMetadata(context.manifest, artifact);

    if (options.writeFiles !== false) {
        context.writeJsonFile(ARTIFACT_OUTPUT_PATH, artifact);
        context.writeTextFile(REPORT_OUTPUT_PATH, report);
        context.writeProposalManifestFile(PROPOSAL_MANIFEST_PATH, artifact);
    }

    return {
        ok: artifact.failed_regression_case_count === 0,
        status: artifact.failed_regression_case_count === 0 ? 0 : 4,
        artifact,
        report,
        updated_manifest: updatedManifest,
    };
}

async function runCli(options = {}) {
    const writeFiles = process.env.PAGEPROPS_NO_WRITE === '1' ? false : (options.writeFiles !== false);
    const result = await runIdentityContractRegressionExecution({ writeFiles }, options);
    process.stdout.write(
        `${JSON.stringify(
            {
                ok: result.ok,
                status: result.status,
                phase: PHASE,
                artifact: ARTIFACT_OUTPUT_PATH,
                report: REPORT_OUTPUT_PATH,
                regression_execution_status: result.artifact.regression_execution_status,
                executed_regression_case_count: result.artifact.executed_regression_case_count,
                passed_regression_case_count: result.artifact.passed_regression_case_count,
                failed_regression_case_count: result.artifact.failed_regression_case_count,
                blocking_rule_verified_count: result.artifact.blocking_rule_verified_count,
                raw_write_execution_ready: result.artifact.raw_write_execution_ready,
                live_fetch_performed: false,
                detail_fetch_performed: false,
                network_request_performed: false,
                db_write_performed: false,
                raw_match_data_insert_performed: false,
                raw_write_execution_performed: false,
                recommended_next_step: result.artifact.recommended_next_step,
            },
            null,
            2
        )}\n`
    );
    return result;
}

module.exports = {
    PHASE,
    PHASE_NAME,
    EXECUTION_STATUS,
    BLOCKED_STATUS,
    AX_EXECUTION_NEXT_STEP,
    NEXT_STEP,
    NEXT_REQUIRED_STEP,
    PROPOSAL_MANIFEST_PATH,
    AX_PLAN_PATH,
    AW_IMPLEMENTATION_PATH,
    AO_RECAPTURE_RESULT_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_OUTPUT_PATH,
    BASE_TARGET_EXTERNAL_ID,
    OBSERVED_MISMATCH_EXTERNAL_ID,
    PROPOSAL_INSERTION_ANCHOR,
    buildFixturePageProps,
    buildFixtureHtml,
    buildCaseTarget,
    buildCaseRecord,
    buildBlockingRuleRecords,
    buildProposalManifestDeltaBlock,
    executeRegressionCases,
    buildArtifact,
    buildReport,
    updateManifestMetadata,
    writeProposalManifestFile,
    loadContext,
    runIdentityContractRegressionExecution,
    runCli,
};

if (require.main === module) {
    runCli()
        .then(result => {
            process.exitCode = result.status;
        })
        .catch(error => {
            process.stderr.write(`${error.stack || error.message}\n`);
            process.exitCode = 1;
        });
}
