'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const {
    classifyDetailCandidateIdentity,
    validateStrictFixtureIdentity,
    FIXTURE_IDENTITY_GUARD_PASSED,
    FIXTURE_IDENTITY_GUARD_BLOCKED,
} = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

const { FotMobSourceInventoryAdapter } = require('../../src/infrastructure/services/FotMobSourceInventoryAdapter');

// --- Test fixtures ---

function positiveControlContext() {
    return {
        schedule_home_team: 'AFC Bournemouth',
        schedule_away_team: 'Manchester City',
        schedule_date: '2026-05-19T18:30:00.000Z',
        league_name: 'Premier League',
        source_home_team: 'AFC Bournemouth',
        source_away_team: 'Manchester City',
        source_match_date: 'Tue, May 19, 2026, 18:30 UTC',
        detail_external_id_candidate: '4813735',
    };
}

function reverseSample467() {
    return {
        schedule_home_team: 'Le Havre',
        schedule_away_team: 'Lens',
        schedule_date: '2025-08-24T15:15:00.000Z',
        league_name: 'Ligue 1',
        source_home_team: 'Lens',
        source_away_team: 'Le Havre',
        source_match_date: 'Sun, Feb 1, 2026, 16:15 UTC',
        detail_external_id_candidate: '4830630',
    };
}

function reverseSample468() {
    return {
        schedule_home_team: 'Lille',
        schedule_away_team: 'Monaco',
        schedule_date: '2025-08-24T18:45:00.000Z',
        league_name: 'Ligue 1',
        source_home_team: 'Monaco',
        source_away_team: 'Lille',
        source_match_date: 'Sun, May 10, 2026, 19:00 UTC',
        detail_external_id_candidate: '4830751',
    };
}

function unknownOnlyCandidate() {
    return {
        detail_external_id_candidate: '4830999',
    };
}

function sameTeamPairWrongDate() {
    return {
        schedule_home_team: 'Paris FC',
        schedule_away_team: 'Angers',
        schedule_date: '2025-08-17T15:15:00.000Z',
        source_home_team: 'Paris FC',
        source_away_team: 'Angers',
        source_match_date: 'Sun, Jan 25, 2026, 16:15 UTC',
        detail_external_id_candidate: '4830627',
    };
}

// --- classifyDetailCandidateIdentity tests ---

test('ADG14 classifyDetailCandidateIdentity: positive control passes', () => {
    const result = classifyDetailCandidateIdentity(positiveControlContext());

    assert.equal(result.detail_identity_candidate_status, 'accepted_validated');
    assert.equal(result.fixture_identity_guard_status, FIXTURE_IDENTITY_GUARD_PASSED);
    assert.equal(result.correction_needed, false);
    assert.equal(result.raw_write_execution_ready, false);
    assert.equal(result.home_away_orientation, 'matches');
    assert.equal(result.detail_external_id_candidate, '4813735');
});

test('ADG14 classifyDetailCandidateIdentity: reverse sample 467 blocked', () => {
    const result = classifyDetailCandidateIdentity(reverseSample467());

    assert.equal(result.detail_identity_candidate_status, 'rejected_reverse_fixture_mapping');
    assert.equal(result.fixture_identity_guard_status, FIXTURE_IDENTITY_GUARD_BLOCKED);
    assert.equal(result.correction_needed, true);
    assert.equal(result.correction_type, 'reject_candidate');
    assert.equal(result.home_away_orientation, 'reversed');
    assert.ok(result.date_delta_days > 100, `delta=${result.date_delta_days} must be >100`);
    assert.ok(result.correction_actions.includes('reject_candidate'));
});

test('ADG14 classifyDetailCandidateIdentity: reverse sample 468 blocked', () => {
    const result = classifyDetailCandidateIdentity(reverseSample468());

    assert.equal(result.fixture_identity_guard_status, FIXTURE_IDENTITY_GUARD_BLOCKED);
    assert.equal(result.detail_identity_candidate_status, 'rejected_reverse_fixture_mapping');
    assert.equal(result.home_away_orientation, 'reversed');
});

test('ADG14 classifyDetailCandidateIdentity: all seven reverse samples blocked', () => {
    const samples = [
        { id: '4830458', schedule_home: 'Angers', schedule_away: 'Paris FC', source_home: 'Paris FC', source_away: 'Angers', sched_date: '2025-08-17T15:15:00.000Z', src_date: 'Sun, Jan 25, 2026, 16:15 UTC' },
        { id: '4830464', schedule_home: 'Nantes', schedule_away: 'Paris Saint-Germain', source_home: 'Paris Saint-Germain', source_away: 'Nantes', sched_date: '2025-08-17T18:45:00.000Z', src_date: 'Wed, Apr 22, 2026, 17:00 UTC' },
        { id: '4830467', schedule_home: 'Le Havre', schedule_away: 'Lens', source_home: 'Lens', source_away: 'Le Havre', sched_date: '2025-08-24T15:15:00.000Z', src_date: 'Sun, Feb 1, 2026, 16:15 UTC' },
        { id: '4830468', schedule_home: 'Lille', schedule_away: 'Monaco', source_home: 'Monaco', source_away: 'Lille', sched_date: '2025-08-24T18:45:00.000Z', src_date: 'Sun, May 10, 2026, 19:00 UTC' },
        { id: '4830469', schedule_home: 'Lorient', schedule_away: 'Rennes', source_home: 'Rennes', source_away: 'Lorient', sched_date: '2025-08-24T13:00:00.000Z', src_date: 'Sun, Jan 25, 2026, 14:00 UTC' },
        { id: '4830470', schedule_home: 'Lyon', schedule_away: 'Metz', source_home: 'Metz', source_away: 'Lyon', sched_date: '2025-08-23T19:05:00.000Z', src_date: 'Sat, Jan 24, 2026, 18:00 UTC' },
        { id: '4830471', schedule_home: 'Marseille', schedule_away: 'Paris FC', source_home: 'Paris FC', source_away: 'Marseille', sched_date: '2025-08-23T15:00:00.000Z', src_date: 'Sat, Jan 31, 2026, 16:00 UTC' },
    ];

    for (const s of samples) {
        const result = classifyDetailCandidateIdentity({
            schedule_home_team: s.schedule_home,
            schedule_away_team: s.schedule_away,
            schedule_date: s.sched_date,
            source_home_team: s.source_home,
            source_away_team: s.source_away,
            source_match_date: s.src_date,
            detail_external_id_candidate: s.id,
        });

        assert.equal(result.fixture_identity_guard_status, FIXTURE_IDENTITY_GUARD_BLOCKED, `${s.id} must be blocked`);
        assert.equal(result.correction_needed, true, `${s.id} must need correction`);
        assert.equal(result.raw_write_execution_ready, false);
        assert.ok(result.correction_actions.includes('require_strict_home_away_date_guard'));
    }
});

test('ADG14 classifyDetailCandidateIdentity: URL hash alone insufficient', () => {
    const result = classifyDetailCandidateIdentity(unknownOnlyCandidate());

    assert.equal(result.detail_identity_candidate_status, 'unknown_insufficient_evidence');
    assert.equal(result.fixture_identity_guard_status, FIXTURE_IDENTITY_GUARD_BLOCKED);
    assert.equal(result.url_hash_alone_insufficient, true);
    assert.equal(result.raw_write_execution_ready, false);
});

test('ADG14 classifyDetailCandidateIdentity: same team pair wrong date blocks', () => {
    const result = classifyDetailCandidateIdentity(sameTeamPairWrongDate());

    assert.equal(result.fixture_identity_guard_status, FIXTURE_IDENTITY_GUARD_BLOCKED);
    assert.ok(result.date_delta_days > 100);
    assert.ok(result.correction_actions.includes('require_strict_home_away_date_guard'));
});

test('ADG14 SourceInventoryAdapter toManifestCandidateSeed produces candidate status fields', () => {
    const adapter = new FotMobSourceInventoryAdapter();

    const seed = adapter.toManifestCandidateSeed(
        {
            external_id: '4813735',
            home_team: 'AFC Bournemouth',
            away_team: 'Manchester City',
            match_date: '2026-05-19T18:30:00.000Z',
            league_name: 'Premier League',
        },
        1,
        {
            source_page_url: 'https://www.fotmob.com/matches/manchester-city-vs-afc-bournemouth/2feiv3#4813735',
            source_url_fragment_external_id: '4813735',
            source_inventory_record_key: 'l1_api_data_leagues:test:4813735',
        }
    );

    assert.equal(seed.external_id, '4813735');
    assert.equal(seed.detail_external_id_candidate, '4813735',
        'detail hash preserved as evidence');
    assert.ok('detail_identity_candidate_status' in seed, 'must have candidate status field');
    // Without source observed teams, classification is unknown_insufficient_evidence
    // This is correct: URL hash is preserved but not validated without observed data
    assert.ok('correction_needed' in seed, 'must have correction field');
    assert.ok('raw_write_execution_ready' in seed);
    assert.equal(seed.raw_write_execution_ready, false);
});

test('ADG14 SourceInventoryAdapter toManifestCandidateSeed sets rejected when home/away inverted', () => {
    const adapter = new FotMobSourceInventoryAdapter();

    const seed = adapter.toManifestCandidateSeed(
        {
            external_id: '4830458',
            home_team: 'Angers',
            away_team: 'Paris FC',
            match_date: '2025-08-17T15:15:00.000Z',
            league_name: 'Ligue 1',
        },
        1,
        {
            source_page_url: 'https://www.fotmob.com/matches/paris-fc-vs-angers/1qlitv#4830458',
            source_url_fragment_external_id: '4830458',
            source_inventory_record_key: 'l1_api_data_leagues:test:4830458',
            source_home_team: 'Paris FC',
            source_away_team: 'Angers',
            source_match_date: 'Sun, Jan 25, 2026, 16:15 UTC',
        }
    );

    assert.equal(seed.external_id, '4830458');
    assert.equal(seed.detail_identity_candidate_status, 'rejected_reverse_fixture_mapping',
        'inverted candidate must be rejected at generation time');
    assert.equal(seed.correction_needed, true);
    assert.equal(seed.raw_write_execution_ready, false);
});

test('ADG14 validateStrictFixtureIdentity still works for integration', () => {
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
});
