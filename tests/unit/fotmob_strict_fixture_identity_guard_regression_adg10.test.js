'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const {
    runRegression,
    buildArtifact,
} = require('../../scripts/ops/fotmob_strict_fixture_identity_guard_regression_adg10');

const {
    validateStrictFixtureIdentity,
    FIXTURE_IDENTITY_GUARD_PASSED,
    FIXTURE_IDENTITY_GUARD_BLOCKED,
} = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

function minimalProposal() {
    return {
        candidate_targets: [
            {
                target_id: 'test:53_20252026_4830458',
                match_id: '53_20252026_4830458',
                external_id: '4830458',
                schedule_home_team: 'Angers',
                schedule_away_team: 'Paris FC',
                schedule_date: '2025-08-17T15:15:00.000Z',
                league_name: 'Ligue 1',
                home_team: 'Angers',
                away_team: 'Paris FC',
            },
            {
                target_id: 'test:53_20252026_4830999',
                match_id: '53_20252026_4830999',
                external_id: '4830999',
                schedule_home_team: 'Team X',
                schedule_away_team: 'Team Y',
                schedule_date: '2025-08-17T15:15:00.000Z',
                league_name: 'Ligue 1',
            },
        ],
        known_completed_targets: [],
    };
}

function minimalAdg8Result() {
    return {
        audit_results: [
            {
                schedule_external_id: '4830458',
                observed_detail_id: '4830627',
                observed_home_team: 'Paris FC',
                observed_away_team: 'Angers',
                observed_match_date: 'Sun, Jan 25, 2026, 16:15 UTC',
                audit_classification: 'reverse_fixture_mapping_error',
            },
            {
                schedule_external_id: '4813735',
                observed_detail_id: '4813735',
                observed_home_team: 'AFC Bournemouth',
                observed_away_team: 'Manchester City',
                observed_match_date: 'Tue, May 19, 2026, 18:30 UTC',
                audit_classification: 'correct_mapping',
            },
        ],
    };
}

function minimalSuspendedReview() {
    return {
        review_cases: [],
    };
}

test('ADG10 regression blocks reverse fixture sample with observed evidence', () => {
    const result = runRegression(
        {},
        {
            proposal: minimalProposal(),
            adg8Result: minimalAdg8Result(),
            suspendedReview: minimalSuspendedReview(),
            enrichedArtifact: { enriched_targets: [] },
        }
    );

    const reverseTarget = result.request_contract_targets.find(t => t.schedule_external_id === '4830458');
    assert.ok(reverseTarget, '4830458 must be in regression');
    assert.equal(reverseTarget.fixture_identity_guard_status, FIXTURE_IDENTITY_GUARD_BLOCKED);
    assert.equal(reverseTarget.audit_classification, 'reverse_fixture_mapping_error');
    assert.equal(reverseTarget.correction_needed, true);
    assert.equal(reverseTarget.raw_write_execution_ready, false);
    assert.ok(reverseTarget.date_delta_days >= 150);
});

test('ADG10 regression classifies targets without observed evidence as missing_observed_identity_evidence', () => {
    const result = runRegression(
        {},
        {
            proposal: minimalProposal(),
            adg8Result: minimalAdg8Result(),
            suspendedReview: minimalSuspendedReview(),
            enrichedArtifact: { enriched_targets: [] },
        }
    );

    const missingTarget = result.request_contract_targets.find(t => t.schedule_external_id === '4830999');
    assert.ok(missingTarget, '4830999 must be in regression');
    assert.equal(missingTarget.fixture_identity_guard_status, FIXTURE_IDENTITY_GUARD_BLOCKED);
    assert.equal(missingTarget.audit_classification, 'missing_observed_identity_evidence');
    assert.equal(missingTarget.correction_needed, false);
    assert.equal(missingTarget.has_observed_identity_evidence, false);
});

test('ADG10 regression preserves positive control #4813735 as correct_mapping', () => {
    const result = runRegression(
        {},
        {
            proposal: minimalProposal(),
            adg8Result: minimalAdg8Result(),
            suspendedReview: minimalSuspendedReview(),
            enrichedArtifact: { enriched_targets: [] },
        }
    );

    assert.equal(result.positive_controls.length, 1);
    const pc = result.positive_controls[0];
    assert.equal(pc.schedule_external_id, '4813735');
    assert.equal(pc.fixture_identity_guard_status, FIXTURE_IDENTITY_GUARD_PASSED);
    assert.equal(pc.audit_classification, 'correct_mapping');
    assert.equal(pc.raw_write_execution_ready, false);
});

test('ADG10 regression marks suspended targets as suspended_reference_still_blocked', () => {
    const result = runRegression(
        {},
        {
            proposal: {
                candidate_targets: [
                    {
                        target_id: 'test:suspended',
                        external_id: '4830998',
                        schedule_home_team: 'Team A',
                        schedule_away_team: 'Team B',
                        schedule_date: '2025-08-16T00:00:00.000Z',
                        league_name: 'Ligue 1',
                    },
                ],
                known_completed_targets: [],
            },
            adg8Result: { audit_results: [] },
            suspendedReview: {
                review_cases: [
                    {
                        current_effective_status: 'suspended',
                        requested_external_id: '4830998',
                    },
                ],
            },
            enrichedArtifact: { enriched_targets: [] },
        }
    );

    const suspended = result.suspended_preservation_targets[0];
    assert.ok(suspended, 'must have suspended target');
    assert.equal(suspended.fixture_identity_guard_status, FIXTURE_IDENTITY_GUARD_BLOCKED);
    assert.equal(suspended.audit_classification, 'suspended_reference_still_blocked');
    assert.equal(suspended.raw_write_execution_ready, false);
    assert.equal(suspended.is_suspended_reference, true);
});

test('ADG10 regression completed targets are excluded from regression scope', () => {
    const result = runRegression(
        {},
        {
            proposal: {
                candidate_targets: [
                    {
                        target_id: 'test:active',
                        external_id: '4830999',
                        schedule_home_team: 'Team X',
                        schedule_away_team: 'Team Y',
                        schedule_date: '2025-08-17T00:00:00.000Z',
                        league_name: 'Ligue 1',
                    },
                    {
                        target_id: 'test:completed',
                        external_id: '4830750',
                        schedule_home_team: 'Done',
                        schedule_away_team: 'Done',
                        schedule_date: '2025-05-01T00:00:00.000Z',
                        league_name: 'Ligue 1',
                    },
                ],
                known_completed_targets: [{ external_id: '4830750' }],
            },
            adg8Result: { audit_results: [] },
            suspendedReview: { review_cases: [] },
            enrichedArtifact: { enriched_targets: [] },
        }
    );

    const activeIds = result.request_contract_targets.map(t => t.schedule_external_id);
    assert.ok(activeIds.includes('4830999'), 'active target must be included');
    assert.ok(!activeIds.includes('4830750'), 'completed target must be excluded');
});

test('ADG10 buildArtifact produces valid counts with no-write safety', () => {
    const artifact = buildArtifact({
        proposal: minimalProposal(),
        adg8Result: minimalAdg8Result(),
        suspendedReview: minimalSuspendedReview(),
        enrichedArtifact: { enriched_targets: [] },
        generatedAt: '2026-05-28T00:00:00.000Z',
    });

    assert.equal(artifact.regression_execution_performed, true);
    assert.equal(artifact.no_live_fetch, true);
    assert.equal(artifact.no_db_write, true);
    assert.equal(artifact.no_raw_write, true);
    assert.equal(artifact.no_suspension_reversal, true);
    assert.equal(artifact.source_inventory_mutation_performed, false);
    assert.equal(artifact.candidate_mutation_performed, false);
    assert.equal(artifact.raw_write_execution_performed, false);
    assert.equal(artifact.raw_write_ready_count, 0);
    assert.equal(artifact.re_acceptance_candidate_count, 0);
    assert.equal(artifact.positive_control_count, 1);
    assert.equal(artifact.total_request_contract_targets, 2);
    assert.ok(typeof artifact.recommended_next_step === 'string');
});

test('ADG10 regression raw_write_ready always false', () => {
    const artifact = buildArtifact({
        proposal: minimalProposal(),
        adg8Result: minimalAdg8Result(),
        suspendedReview: minimalSuspendedReview(),
        enrichedArtifact: { enriched_targets: [] },
    });

    for (const t of artifact.request_contract_regression) {
        assert.equal(t.raw_write_execution_ready, false);
    }
    for (const t of artifact.suspended_preservation_regression) {
        assert.equal(t.raw_write_execution_ready, false);
    }
    for (const t of artifact.positive_control_regression) {
        assert.equal(t.raw_write_execution_ready, false);
    }
});

test('ADG10 guard integration: validateStrictFixtureIdentity is the runtime code', () => {
    const result = validateStrictFixtureIdentity({
        schedule_external_id: '4813735',
        detail_external_id_candidate: '4813735',
        expected_home_team: 'AFC Bournemouth',
        expected_away_team: 'Manchester City',
        observed_detail_id: '4813735',
        observed_home_team: 'AFC Bournemouth',
        observed_away_team: 'Manchester City',
        expected_match_date: '2026-05-19T18:30:00.000Z',
        observed_match_date: 'Tue, May 19, 2026, 18:30 UTC',
    });

    assert.equal(result.fixture_identity_guard_status, FIXTURE_IDENTITY_GUARD_PASSED);
    assert.equal(result.audit_classification, 'correct_mapping');
});
