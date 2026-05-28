#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21-ADG10';
const STATUS = 'completed_strict_fixture_identity_guard_regression';

const PROPOSAL_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const ADG8_RESULT_PATH = 'docs/_manifests/fotmob_identity_mapping_source_inventory_audit_result.adg8.json';
const SUSPENDED_REVIEW_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.suspended_target_review_result.phase521l2v3ba.json';
const ENRICHED_TARGETS_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_targets.phase521l2v3aa.json';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_strict_fixture_identity_guard_regression.adg10.json';
const REPORT_OUTPUT_PATH = 'docs/_reports/FOTMOB_STRICT_FIXTURE_IDENTITY_GUARD_REGRESSION_ADG10.md';

const {
    validateStrictFixtureIdentity,
    FIXTURE_IDENTITY_GUARD_PASSED,
    FIXTURE_IDENTITY_GUARD_BLOCKED,
} = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

function absolutePath(filePath) {
    return path.isAbsolute(filePath) ? filePath : path.join(PROJECT_ROOT, filePath);
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

function buildAdg8ObservedMap(adg8Result = {}) {
    const map = new Map();
    for (const record of adg8Result.audit_results || []) {
        if (record.schedule_external_id) {
            map.set(record.schedule_external_id, {
                observed_detail_id: record.observed_detail_id,
                observed_home_team: record.observed_home_team,
                observed_away_team: record.observed_away_team,
                observed_match_date: record.observed_match_date,
                observed_competition: record.observed_competition,
                adg8_classification: record.audit_classification,
                is_suspended:
                    record.audit_classification === 'suspended_reference_still_blocked' ||
                    record.reference_status === 'blocked_reference_only_no_unsuspend',
            });
        }
    }
    return map;
}

function buildSuspendedSet(suspendedReview = {}) {
    const suspended = new Set();
    for (const c of suspendedReview.review_cases || []) {
        if (c.current_effective_status === 'suspended' && c.requested_external_id) {
            suspended.add(String(c.requested_external_id));
        }
    }
    return suspended;
}

function buildEnrichedMap(enrichedArtifact = {}) {
    const map = new Map();
    for (const t of enrichedArtifact.enriched_targets || []) {
        if (t.schedule_external_id) {
            map.set(String(t.schedule_external_id), t);
        }
    }
    return map;
}

function buildCompletedSet(proposal = {}) {
    return new Set(
        (proposal.known_completed_targets || []).map(t => String(t.external_id))
    );
}

function regressTarget(candidate = {}, observedEvidence = null, isSuspended = false) {
    const scheduleExternalId = String(candidate.external_id || candidate.schedule_external_id || '');
    const expectedHome = candidate.schedule_home_team || candidate.home_team;
    const expectedAway = candidate.schedule_away_team || candidate.away_team;
    const expectedDate = candidate.schedule_date || candidate.match_date || candidate.kickoff_time;
    const expectedCompetition = candidate.league_name || null;

    const base = {
        schedule_external_id: scheduleExternalId,
        target_id: candidate.target_id || null,
        match_id: candidate.match_id || null,
        expected_home_team: expectedHome,
        expected_away_team: expectedAway,
        expected_match_date: expectedDate,
        expected_competition: expectedCompetition,
        is_suspended_reference: isSuspended,
        has_observed_identity_evidence: Boolean(observedEvidence),
    };

    if (isSuspended) {
        return {
            ...base,
            fixture_identity_guard_status: FIXTURE_IDENTITY_GUARD_BLOCKED,
            audit_classification: 'suspended_reference_still_blocked',
            correction_needed: false,
            raw_write_execution_ready: false,
            observed_detail_id: null,
            observed_home_team: null,
            observed_away_team: null,
            observed_match_date: null,
            home_away_orientation_status: null,
            date_delta_days: null,
            blockers: ['suspended_reference_still_blocked'],
        };
    }

    if (!observedEvidence) {
        return {
            ...base,
            fixture_identity_guard_status: FIXTURE_IDENTITY_GUARD_BLOCKED,
            audit_classification: 'missing_observed_identity_evidence',
            correction_needed: false,
            raw_write_execution_ready: false,
            observed_detail_id: null,
            observed_home_team: null,
            observed_away_team: null,
            observed_match_date: null,
            home_away_orientation_status: null,
            date_delta_days: null,
            blockers: ['missing_observed_identity_evidence'],
        };
    }

    const guardInput = {
        schedule_external_id: scheduleExternalId,
        detail_external_id_candidate: scheduleExternalId,
        expected_home_team: expectedHome,
        expected_away_team: expectedAway,
        expected_match_date: expectedDate,
        expected_competition: expectedCompetition,
        observed_detail_id: observedEvidence.observed_detail_id,
        observed_home_team: observedEvidence.observed_home_team,
        observed_away_team: observedEvidence.observed_away_team,
        observed_match_date: observedEvidence.observed_match_date,
        observed_competition: observedEvidence.observed_competition,
        is_suspended_reference: isSuspended,
    };

    const guardResult = validateStrictFixtureIdentity(guardInput);

    return {
        ...base,
        fixture_identity_guard_status: guardResult.fixture_identity_guard_status,
        fixture_identity_guard_reason: guardResult.fixture_identity_guard_reason,
        audit_classification: guardResult.audit_classification,
        observed_detail_id: guardResult.observed_detail_id,
        observed_home_team: guardResult.observed_home_team,
        observed_away_team: guardResult.observed_away_team,
        observed_match_date: guardResult.observed_match_date,
        home_away_orientation_status: guardResult.home_away_orientation_status,
        date_delta_days: guardResult.date_delta_days,
        correction_needed: guardResult.correction_needed,
        correction_type: guardResult.correction_type,
        correction_actions: guardResult.correction_actions,
        raw_write_execution_ready: false,
        detail_identity_candidate_validated: guardResult.detail_identity_candidate_validated,
        url_hash_alone_insufficient: guardResult.url_hash_alone_insufficient,
        blockers: guardResult.blockers,
    };
}

function runRegression(options = {}, dependencies = {}) {
    const proposal = dependencies.proposal || readJsonFile(PROPOSAL_PATH);
    const adg8Result = dependencies.adg8Result || readJsonFile(ADG8_RESULT_PATH);
    const suspendedReview = dependencies.suspendedReview || readJsonFile(SUSPENDED_REVIEW_PATH);
    const enrichedArtifact = dependencies.enrichedArtifact || readJsonFile(ENRICHED_TARGETS_PATH);

    const observedMap = buildAdg8ObservedMap(adg8Result);
    const suspendedSet = buildSuspendedSet(suspendedReview);
    const enrichedMap = buildEnrichedMap(enrichedArtifact);
    const completedSet = buildCompletedSet(proposal);

    const requestContractTargets = [];
    const suspendedPreservationResults = [];
    const positiveControlResults = [];

    for (const candidate of proposal.candidate_targets || []) {
        const externalId = String(candidate.external_id || '');
        if (completedSet.has(externalId)) continue;

        const isSuspended = suspendedSet.has(externalId);
        const observedEvidence = observedMap.get(externalId) || null;
        const result = regressTarget(candidate, observedEvidence, isSuspended);

        if (isSuspended) {
            suspendedPreservationResults.push(result);
        } else {
            requestContractTargets.push(result);
        }
    }

    // Add positive control #4813735 from ADG8
    const positiveObserved = observedMap.get('4813735');
    if (positiveObserved) {
        const pc = regressTarget(
            {
                external_id: '4813735',
                home_team: 'AFC Bournemouth',
                away_team: 'Manchester City',
                match_date: '2026-05-19T18:30:00.000Z',
                league_name: 'Premier League',
                target_id: 'positive_control_4813735',
            },
            positiveObserved,
            false
        );
        positiveControlResults.push(pc);
    }

    return {
        request_contract_targets: requestContractTargets,
        suspended_preservation_targets: suspendedPreservationResults,
        positive_controls: positiveControlResults,
    };
}

function countBy(list = [], pred) {
    return list.filter(pred).length;
}

function buildArtifact(deps = {}) {
    const generatedAt = deps.generatedAt || new Date().toISOString();
    const { request_contract_targets, suspended_preservation_targets, positive_controls } =
        runRegression({}, deps);

    const allTargets = [...request_contract_targets, ...suspended_preservation_targets];

    const summary = {
        positive_control_count: positive_controls.length,
        total_request_contract_targets: request_contract_targets.length,
        total_suspended_targets: suspended_preservation_targets.length,
        guard_passed_count: countBy(
            allTargets,
            r => r.fixture_identity_guard_status === FIXTURE_IDENTITY_GUARD_PASSED
        ),
        guard_blocked_count: countBy(
            allTargets,
            r => r.fixture_identity_guard_status === FIXTURE_IDENTITY_GUARD_BLOCKED
        ),
        reverse_fixture_mapping_error_count: countBy(
            allTargets,
            r => r.audit_classification === 'reverse_fixture_mapping_error'
        ),
        home_away_inversion_count: countBy(
            allTargets,
            r => r.audit_classification === 'home_away_inversion'
        ),
        same_team_pair_wrong_leg_count: countBy(
            allTargets,
            r => r.audit_classification === 'same_team_pair_wrong_leg'
        ),
        date_mismatch_count: countBy(
            allTargets,
            r => r.blockers.includes('date_mismatch')
        ),
        competition_mismatch_count: countBy(
            allTargets,
            r => r.audit_classification === 'competition_mismatch'
        ),
        missing_observed_identity_evidence_count: countBy(
            allTargets,
            r => r.audit_classification === 'missing_observed_identity_evidence'
        ),
        insufficient_source_inventory_evidence_count: countBy(
            allTargets,
            r => r.audit_classification === 'insufficient_source_inventory_evidence'
        ),
        correction_candidate_required_count: countBy(
            allTargets,
            r => r.correction_needed === true
        ),
        suspended_still_blocked_count: countBy(
            allTargets,
            r => r.audit_classification === 'suspended_reference_still_blocked'
        ),
        raw_write_ready_count: 0,
        re_acceptance_candidate_count: 0,
    };

    const recommendedNextStep =
        summary.missing_observed_identity_evidence_count > 30
            ? 'evidence_acquisition_planning_for_targets_without_observed_identity; do not raw write'
            : summary.reverse_fixture_mapping_error_count > 3
                ? 'source_inventory_correction_implementation_planning; do not raw write'
                : 'bounded_no_write_page_route_verification_planning; do not raw write';

    return {
        schema_version: 'fotmob_strict_fixture_identity_guard_regression_adg10_v1',
        phase: PHASE,
        generated_at: generatedAt,
        adg10_regression_execution_status: STATUS,
        regression_execution_performed: true,
        no_live_fetch: true,
        no_network_request: true,
        no_browser_automation: true,
        no_direct_api_probing: true,
        no_db_write: true,
        no_raw_write: true,
        no_raw_match_data_insert: true,
        no_re_acceptance: true,
        no_suspension_reversal: true,
        source_inventory_mutation_performed: false,
        candidate_mutation_performed: false,
        db_write_performed: false,
        raw_write_execution_performed: false,
        full_payload_saved: false,
        full_payload_printed: false,
        ...summary,
        recommended_next_step: recommendedNextStep,
        request_contract_regression: request_contract_targets,
        suspended_preservation_regression: suspended_preservation_targets,
        positive_control_regression: positive_controls,
    };
}

function buildReport(artifact = {}) {
    const lines = [
        '# FotMob Strict Fixture Identity Guard Regression ADG10',
        '',
        `- Phase: ${artifact.phase}`,
        `- Status: ${artifact.adg10_regression_execution_status}`,
        `- regression_execution_performed=true`,
        '',
        '## Counts',
        '',
        `| Metric | Count |`,
        `| --- | --- |`,
        `| positive_control | ${artifact.positive_control_count} |`,
        `| request_contract_targets | ${artifact.total_request_contract_targets} |`,
        `| suspended_targets | ${artifact.total_suspended_targets} |`,
        `| guard_passed | ${artifact.guard_passed_count} |`,
        `| guard_blocked | ${artifact.guard_blocked_count} |`,
        `| reverse_fixture_mapping_error | ${artifact.reverse_fixture_mapping_error_count} |`,
        `| home_away_inversion | ${artifact.home_away_inversion_count} |`,
        `| same_team_pair_wrong_leg | ${artifact.same_team_pair_wrong_leg_count} |`,
        `| date_mismatch | ${artifact.date_mismatch_count} |`,
        `| missing_observed_identity_evidence | ${artifact.missing_observed_identity_evidence_count} |`,
        `| correction_candidate_required | ${artifact.correction_candidate_required_count} |`,
        `| suspended_still_blocked | ${artifact.suspended_still_blocked_count} |`,
        `| raw_write_ready | ${artifact.raw_write_ready_count} |`,
        `| re_acceptance_candidate | ${artifact.re_acceptance_candidate_count} |`,
        '',
        '## Request Contract Target Regression',
        '',
        '| external_id | expected_teams | classification | status | correction | date_delta |',
        '| --- | --- | --- | --- | --- | --- |',
    ];

    for (const r of artifact.request_contract_regression || []) {
        const teams = `${r.expected_home_team || '?'} vs ${r.expected_away_team || '?'}`;
        lines.push(
            `| ${r.schedule_external_id} | ${teams} | ${r.audit_classification} | ${r.fixture_identity_guard_status} | ${r.correction_needed} | ${r.date_delta_days ?? 'null'} |`
        );
    }

    lines.push(
        '',
        '## Suspended Preservation Regression',
        '',
        '| external_id | classification | status |',
        '| --- | --- | --- |',
    );

    for (const r of artifact.suspended_preservation_regression || []) {
        lines.push(
            `| ${r.schedule_external_id} | ${r.audit_classification} | ${r.fixture_identity_guard_status} |`
        );
    }

    lines.push(
        '',
        '## Positive Control',
        '',
        '| external_id | classification | status |',
        '| --- | --- | --- |',
    );

    for (const r of artifact.positive_control_regression || []) {
        lines.push(
            `| ${r.schedule_external_id} | ${r.audit_classification} | ${r.fixture_identity_guard_status} |`
        );
    }

    lines.push(
        '',
        '## Safety',
        '',
        '- no live fetch / network request / browser automation / direct API probing',
        '- no DB writes / raw writes / raw_match_data inserts',
        '- no re-acceptance / suspension reversal',
        '- no source inventory mutation / candidate mutation execution',
        '- no full payload saved',
        '- raw_write_ready_count=0',
        '',
        `## Recommended Next Step`,
        '',
        artifact.recommended_next_step
    );

    return `${lines.join('\n')}\n`;
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = { writeFiles: true, help: false };
    for (const arg of argv) {
        if (arg === '--help' || arg === '-h') { options.help = true; continue; }
        if (arg === '--write-files=false' || arg === '--write-files=no') {
            options.writeFiles = false; continue;
        }
    }
    return options;
}

function runAdg10(options = {}, dependencies = {}) {
    const artifact = buildArtifact(dependencies);
    const report = buildReport(artifact);
    if (options.writeFiles !== false) {
        writeJsonFile(ARTIFACT_OUTPUT_PATH, artifact);
        writeTextFile(REPORT_OUTPUT_PATH, report);
    }
    return { ok: true, artifact, report };
}

function main(argv = process.argv.slice(2)) {
    const options = parseArgs(argv);
    if (options.help) {
        process.stdout.write(
            'Usage: node scripts/ops/fotmob_strict_fixture_identity_guard_regression_adg10.js [--write-files=false]\n'
        );
        return { status: 0 };
    }
    const result = runAdg10(options);
    process.stdout.write(
        `${JSON.stringify(
            {
                adg10_regression_execution_status: result.artifact.adg10_regression_execution_status,
                total_request_contract_targets: result.artifact.total_request_contract_targets,
                total_suspended_targets: result.artifact.total_suspended_targets,
                guard_passed_count: result.artifact.guard_passed_count,
                guard_blocked_count: result.artifact.guard_blocked_count,
                missing_observed_identity_evidence_count: result.artifact.missing_observed_identity_evidence_count,
                correction_candidate_required_count: result.artifact.correction_candidate_required_count,
                suspended_still_blocked_count: result.artifact.suspended_still_blocked_count,
                raw_write_ready_count: result.artifact.raw_write_ready_count,
            },
            null,
            2
        )}\n`
    );
    return { status: 0 };
}

module.exports = {
    PHASE, STATUS,
    PROPOSAL_PATH, ADG8_RESULT_PATH, SUSPENDED_REVIEW_PATH,
    ARTIFACT_OUTPUT_PATH, REPORT_OUTPUT_PATH,
    buildAdg8ObservedMap, buildSuspendedSet, buildEnrichedMap,
    regressTarget, runRegression, buildArtifact, buildReport, runAdg10, main,
};

if (require.main === module) {
    try { process.exitCode = main().status; } catch (error) {
        process.stderr.write(`${error.stack || error.message}\n`);
        process.exitCode = 1;
    }
}
