'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const {
    validateStrictFixtureIdentity,
    FIXTURE_IDENTITY_GUARD_PASSED,
    FIXTURE_IDENTITY_GUARD_BLOCKED,
} = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

// --- Test data fixtures ---

function positiveControl() {
    return {
        schedule_external_id: '4813735',
        detail_external_id_candidate: '4813735',
        expected_home_team: 'AFC Bournemouth',
        expected_away_team: 'Manchester City',
        observed_detail_id: '4813735',
        observed_home_team: 'AFC Bournemouth',
        observed_away_team: 'Manchester City',
        expected_match_date: '2026-05-19T18:30:00.000Z',
        observed_match_date: 'Tue, May 19, 2026, 18:30 UTC',
    };
}

function reverseSample458() {
    return {
        schedule_external_id: '4830458',
        detail_external_id_candidate: '4830458',
        expected_home_team: 'Angers',
        expected_away_team: 'Paris FC',
        observed_detail_id: '4830627',
        observed_home_team: 'Paris FC',
        observed_away_team: 'Angers',
        expected_match_date: '2025-08-17T15:15:00.000Z',
        observed_match_date: 'Sun, Jan 25, 2026, 16:15 UTC',
        expected_competition: 'Ligue 1',
    };
}

function reverseSample459() {
    return {
        schedule_external_id: '4830459',
        detail_external_id_candidate: '4830459',
        expected_home_team: 'Auxerre',
        expected_away_team: 'Lorient',
        observed_detail_id: '4830667',
        observed_home_team: 'Lorient',
        observed_away_team: 'Auxerre',
        expected_match_date: '2025-08-17T15:15:00.000Z',
        observed_match_date: 'Sun, Mar 1, 2026, 16:15 UTC',
        expected_competition: 'Ligue 1',
    };
}

function suspendedRef461() {
    return {
        schedule_external_id: '4830461',
        detail_external_id_candidate: '4830461',
        expected_home_team: 'Lens',
        expected_away_team: 'Lyon',
        observed_detail_id: '4830758',
        observed_home_team: 'Lyon',
        observed_away_team: 'Lens',
        expected_match_date: '2025-08-16T15:00:00.000Z',
        observed_match_date: 'Sun, May 17, 2026, 19:00 UTC',
        expected_competition: 'Ligue 1',
        is_suspended_reference: true,
    };
}

// --- Test suites ---

test('ADG9 positive control #4813735 passes strict fixture identity guard', () => {
    const result = validateStrictFixtureIdentity(positiveControl());

    assert.equal(result.fixture_identity_guard_status, FIXTURE_IDENTITY_GUARD_PASSED);
    assert.equal(result.audit_classification, 'correct_mapping');
    assert.equal(result.detail_identity_candidate_validated, true);
    assert.equal(result.raw_write_execution_ready, false);
    assert.equal(result.correction_needed, false);
    assert.equal(result.home_away_orientation_status, 'matches');
    assert.equal(result.schedule_external_id, '4813735');
});

test('ADG9 positive control teams match in correct order', () => {
    const result = validateStrictFixtureIdentity(positiveControl());

    assert.equal(result.expected_home_team, 'afc bournemouth');
    assert.equal(result.expected_away_team, 'manchester city');
    assert.equal(result.observed_home_team, 'afc bournemouth');
    assert.equal(result.observed_away_team, 'manchester city');
    assert.equal(result.home_away_orientation_status, 'matches');
    assert.equal(result.team_pair_match, true);
});

test('ADG9 reverse sample 4830458 -> 4830627 blocked as reverse_fixture_mapping_error', () => {
    const result = validateStrictFixtureIdentity(reverseSample458());

    assert.equal(result.fixture_identity_guard_status, FIXTURE_IDENTITY_GUARD_BLOCKED);
    assert.equal(result.audit_classification, 'reverse_fixture_mapping_error');
    assert.equal(result.correction_needed, true);
    assert.equal(result.correction_type, 'reject_candidate');
    assert.equal(result.raw_write_execution_ready, false);
    assert.equal(result.home_away_orientation_status, 'reversed');
    assert.equal(result.schedule_external_id, '4830458');
    assert.equal(result.observed_detail_id, '4830627');
    assert.equal(result.rejected_detail_external_id_candidate, '4830458');
    assert.ok(result.date_delta_days >= 150, 'date delta should be >= 150 days');
    assert.ok(result.correction_actions.includes('require_strict_home_away_date_guard'));
    assert.ok(result.blockers.includes('home_away_inversion'));
    assert.ok(result.blockers.includes('date_mismatch'));
    assert.ok(result.blockers.includes('same_team_pair_wrong_leg'));
});

test('ADG9 reverse sample 4830459 -> 4830667 blocked', () => {
    const result = validateStrictFixtureIdentity(reverseSample459());

    assert.equal(result.fixture_identity_guard_status, FIXTURE_IDENTITY_GUARD_BLOCKED);
    assert.equal(result.audit_classification, 'reverse_fixture_mapping_error');
    assert.equal(result.home_away_orientation_status, 'reversed');
    assert.equal(result.observed_detail_id, '4830667');
    assert.ok(result.date_delta_days >= 190, 'date delta should be >= 190 days');
});

test('ADG9 all five reverse samples blocked', () => {
    const samples = [
        { id: '4830458', expected_home: 'Angers', expected_away: 'Paris FC',
            observed_detail_id: '4830627', observed_home: 'Paris FC', observed_away: 'Angers',
            expected_date: '2025-08-17T15:15:00.000Z', observed_date: 'Sun, Jan 25, 2026, 16:15 UTC' },
        { id: '4830459', expected_home: 'Auxerre', expected_away: 'Lorient',
            observed_detail_id: '4830667', observed_home: 'Lorient', observed_away: 'Auxerre',
            expected_date: '2025-08-17T15:15:00.000Z', observed_date: 'Sun, Mar 1, 2026, 16:15 UTC' },
        { id: '4830460', expected_home: 'Brest', expected_away: 'Lille',
            observed_detail_id: '4830648', observed_home: 'Lille', observed_away: 'Brest',
            expected_date: '2025-08-17T13:00:00.000Z', observed_date: 'Sat, Feb 14, 2026, 18:00 UTC' },
        { id: '4830462', expected_home: 'Metz', expected_away: 'Strasbourg',
            observed_detail_id: '4830618', observed_home: 'Strasbourg', observed_away: 'Metz',
            expected_date: '2025-08-17T15:15:00.000Z', observed_date: 'Sun, Jan 18, 2026, 14:00 UTC' },
        { id: '4830464', expected_home: 'Nantes', expected_away: 'Paris Saint-Germain',
            observed_detail_id: '4830689', observed_home: 'Paris Saint-Germain', observed_away: 'Nantes',
            expected_date: '2025-08-17T18:45:00.000Z', observed_date: 'Wed, Apr 22, 2026, 17:00 UTC' },
    ];

    for (const s of samples) {
        const result = validateStrictFixtureIdentity({
            schedule_external_id: s.id,
            detail_external_id_candidate: s.id,
            expected_home_team: s.expected_home,
            expected_away_team: s.expected_away,
            observed_detail_id: s.observed_detail_id,
            observed_home_team: s.observed_home,
            observed_away_team: s.observed_away,
            expected_match_date: s.expected_date,
            observed_match_date: s.observed_date,
        });

        assert.equal(result.fixture_identity_guard_status, FIXTURE_IDENTITY_GUARD_BLOCKED,
            `${s.id} must be blocked`);
        assert.equal(result.correction_needed, true, `${s.id} must need correction`);
        assert.equal(result.correction_type, 'reject_candidate');
        assert.equal(result.raw_write_execution_ready, false);
        assert.ok(result.date_delta_days > 1, `${s.id} must have large date delta`);
    }
});

test('ADG9 date mismatch blocks with delta 154+ days', () => {
    const result = validateStrictFixtureIdentity({
        schedule_external_id: '4830462',
        expected_home_team: 'Metz',
        expected_away_team: 'Strasbourg',
        expected_match_date: '2025-08-17T15:15:00.000Z',
        observed_home_team: 'Strasbourg',
        observed_away_team: 'Metz',
        observed_match_date: 'Sun, Jan 18, 2026, 14:00 UTC',
    });

    assert.equal(result.fixture_identity_guard_status, FIXTURE_IDENTITY_GUARD_BLOCKED);
    assert.ok(result.date_delta_days >= 150);
    assert.ok(result.blockers.includes('date_mismatch'));
});

test('ADG9 URL hash alone insufficient — candidate with only detail_external_id_candidate', () => {
    const result = validateStrictFixtureIdentity({
        schedule_external_id: '4830999',
        detail_external_id_candidate: '4831999',
        expected_home_team: null,
        expected_away_team: null,
        observed_home_team: null,
        observed_away_team: null,
        expected_match_date: null,
        observed_match_date: null,
    });

    assert.equal(result.url_hash_alone_insufficient, true);
    assert.equal(result.detail_identity_candidate_validated, false);
    assert.equal(result.raw_write_execution_ready, false);
    assert.ok(result.blockers.includes('url_hash_alone_insufficient'));
});

test('ADG9 home/away inversion blocks even if team pair matches', () => {
    const result = validateStrictFixtureIdentity({
        schedule_external_id: '5000001',
        detail_external_id_candidate: '5000001',
        expected_home_team: 'Team A',
        expected_away_team: 'Team B',
        observed_detail_id: '5000999',
        observed_home_team: 'Team B',
        observed_away_team: 'Team A',
        expected_match_date: '2025-08-17T15:15:00.000Z',
        observed_match_date: 'Sun, Jan 25, 2026, 16:15 UTC',
    });

    assert.equal(result.fixture_identity_guard_status, FIXTURE_IDENTITY_GUARD_BLOCKED);
    assert.equal(result.home_away_orientation_status, 'reversed');
    assert.equal(result.team_pair_match, true);
    assert.ok(result.blockers.includes('home_away_inversion'));
});

test('ADG9 suspended reference remains blocked with guard', () => {
    const result = validateStrictFixtureIdentity(suspendedRef461());

    assert.equal(result.fixture_identity_guard_status, FIXTURE_IDENTITY_GUARD_BLOCKED);
    assert.equal(result.audit_classification, 'suspended_reference_still_blocked');
    assert.equal(result.is_suspended_reference, true);
    assert.equal(result.correction_needed, false);
    assert.equal(result.raw_write_execution_ready, false);
    assert.ok(result.blockers.includes('suspended_reference_still_blocked'));
});

test('ADG9 recapture path: accepted detail identity with strict check may pass', () => {
    const result = validateStrictFixtureIdentity({
        schedule_external_id: '4813735',
        detail_external_id_candidate: '4813735',
        expected_home_team: 'AFC Bournemouth',
        expected_away_team: 'Manchester City',
        observed_detail_id: '4813735',
        observed_home_team: 'AFC Bournemouth',
        observed_away_team: 'Manchester City',
        expected_match_date: '2026-05-19T18:30:00.000Z',
        observed_match_date: '2026-05-19T18:30:00.000Z',
    });

    assert.equal(result.fixture_identity_guard_status, FIXTURE_IDENTITY_GUARD_PASSED);
    assert.equal(result.detail_identity_candidate_validated, true);
    assert.equal(result.raw_write_execution_ready, false, 'raw write remains false even when guard passes');
});

test('ADG9 guard output has all required fields', () => {
    const result = validateStrictFixtureIdentity(positiveControl());

    const required = [
        'fixture_identity_guard_status',
        'fixture_identity_guard_reason',
        'audit_classification',
        'schedule_external_id',
        'detail_external_id_candidate',
        'rejected_detail_external_id_candidate',
        'observed_reversed_detail_id',
        'observed_detail_id',
        'expected_home_team',
        'expected_away_team',
        'observed_home_team',
        'observed_away_team',
        'expected_match_date',
        'observed_match_date',
        'home_away_orientation_status',
        'date_delta_days',
        'date_within_tolerance',
        'detail_identity_candidate_validated',
        'correction_needed',
        'correction_type',
        'correction_actions',
        'raw_write_execution_ready',
        'blockers',
    ];

    for (const field of required) {
        assert.ok(field in result, `output missing field: ${field}`);
    }

    assert.equal(result.raw_write_execution_ready, false);
});
