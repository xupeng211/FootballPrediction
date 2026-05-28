'use strict';
const assert = require('node:assert/strict');
const test = require('node:test');
const { selectOrientedFixtureRecord, classifyDetailCandidateIdentity, validateStrictFixtureIdentity,
    FIXTURE_IDENTITY_GUARD_PASSED, FIXTURE_IDENTITY_GUARD_BLOCKED } =
    require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

test('ADG17 oriented selection: exact home/away/date match selected', () => {
    const r = selectOrientedFixtureRecord({
        expectedHome: 'Angers', expectedAway: 'Paris FC', expectedDate: '2025-08-17T15:15:00.000Z',
        candidates: [
            { home_team: 'Paris FC', away_team: 'Angers', match_date: '2026-01-25T16:15:00.000Z', external_id: '4830627' },
            { home_team: 'Angers', away_team: 'Paris FC', match_date: '2025-08-17T15:15:00.000Z', external_id: '4830458' },
        ],
    });
    assert.equal(r.status, 'oriented_match_selected');
    assert.equal(r.selected.external_id, '4830458');
    assert.equal(r.raw_write_ready, false);
});

test('ADG17 oriented selection: only reverse available rejects', () => {
    const r = selectOrientedFixtureRecord({
        expectedHome: 'Angers', expectedAway: 'Paris FC', expectedDate: '2025-08-17T15:15:00.000Z',
        candidates: [
            { home_team: 'Paris FC', away_team: 'Angers', match_date: '2026-01-25T16:15:00.000Z', external_id: '4830627' },
        ],
    });
    assert.equal(r.status, 'rejected_reverse_fixture_mapping');
    assert.equal(r.selected, null);
    assert.equal(r.correction_needed, true);
    assert.equal(r.raw_write_ready, false);
});

test('ADG17 oriented selection: positive control team pair passes', () => {
    const r = selectOrientedFixtureRecord({
        expectedHome: 'AFC Bournemouth', expectedAway: 'Manchester City', expectedDate: '2026-05-19T18:30:00.000Z',
        candidates: [
            { home_team: 'AFC Bournemouth', away_team: 'Manchester City', match_date: '2026-05-19T18:30:00.000Z', external_id: '4813735' },
        ],
    });
    assert.equal(r.status, 'oriented_match_selected');
    assert.equal(r.selected.external_id, '4813735');
});

test('ADG17 oriented selection: 17 known reverse samples all rejected', () => {
    const samples = [
        { id: '4830458', expH: 'Angers', expA: 'Paris FC', ed: '2025-08-17T15:15:00.000Z', obsH: 'Paris FC', obsA: 'Angers', od: '2026-01-25T16:15:00.000Z' },
        { id: '4830459', expH: 'Auxerre', expA: 'Lorient', ed: '2025-08-17T15:15:00.000Z', obsH: 'Lorient', obsA: 'Auxerre', od: '2026-03-01T16:15:00.000Z' },
        { id: '4830460', expH: 'Brest', expA: 'Lille', ed: '2025-08-17T13:00:00.000Z', obsH: 'Lille', obsA: 'Brest', od: '2026-02-14T18:00:00.000Z' },
        { id: '4830462', expH: 'Metz', expA: 'Strasbourg', ed: '2025-08-17T15:15:00.000Z', obsH: 'Strasbourg', obsA: 'Metz', od: '2026-01-18T14:00:00.000Z' },
        { id: '4830464', expH: 'Nantes', expA: 'Paris Saint-Germain', ed: '2025-08-17T18:45:00.000Z', obsH: 'Paris Saint-Germain', obsA: 'Nantes', od: '2026-04-22T17:00:00.000Z' },
        { id: '4830467', expH: 'Le Havre', expA: 'Lens', ed: '2025-08-24T15:15:00.000Z', obsH: 'Lens', obsA: 'Le Havre', od: '2026-02-01T16:15:00.000Z' },
        { id: '4830468', expH: 'Lille', expA: 'Monaco', ed: '2025-08-24T18:45:00.000Z', obsH: 'Monaco', obsA: 'Lille', od: '2026-05-10T19:00:00.000Z' },
        { id: '4830469', expH: 'Lorient', expA: 'Rennes', ed: '2025-08-24T13:00:00.000Z', obsH: 'Rennes', obsA: 'Lorient', od: '2026-01-25T14:00:00.000Z' },
        { id: '4830470', expH: 'Lyon', expA: 'Metz', ed: '2025-08-23T19:05:00.000Z', obsH: 'Metz', obsA: 'Lyon', od: '2026-01-24T18:00:00.000Z' },
        { id: '4830471', expH: 'Marseille', expA: 'Paris FC', ed: '2025-08-23T15:00:00.000Z', obsH: 'Paris FC', obsA: 'Marseille', od: '2026-01-31T16:00:00.000Z' },
    ];
    for (const s of samples) {
        const r = selectOrientedFixtureRecord({
            expectedHome: s.expH, expectedAway: s.expA, expectedDate: s.ed,
            candidates: [{ home_team: s.obsH, away_team: s.obsA, match_date: s.od, external_id: s.id }],
        });
        assert.equal(r.status, 'rejected_reverse_fixture_mapping', `${s.id} must be rejected`);
        assert.equal(r.correction_needed, true);
    }
});

test('ADG17 no candidates returns no_candidates status', () => {
    const r = selectOrientedFixtureRecord({ expectedHome: 'A', expectedAway: 'B', candidates: [] });
    assert.equal(r.status, 'no_candidates');
    assert.equal(r.selected, null);
});

test('ADG17 classifyDetailCandidateIdentity still works', () => {
    const r = classifyDetailCandidateIdentity({
        schedule_home_team: 'AFC Bournemouth', schedule_away_team: 'Manchester City',
        source_home_team: 'AFC Bournemouth', source_away_team: 'Manchester City',
        detail_external_id_candidate: '4813735',
    });
    assert.equal(r.detail_identity_candidate_status, 'accepted_validated');
});

test('ADG17 validateStrictFixtureIdentity still works', () => {
    const r = validateStrictFixtureIdentity({
        expected_home_team: 'AFC Bournemouth', expected_away_team: 'Manchester City',
        observed_home_team: 'AFC Bournemouth', observed_away_team: 'Manchester City',
        observed_detail_id: '4813735', detail_external_id_candidate: '4813735',
        expected_match_date: '2026-05-19T18:30:00.000Z', observed_match_date: 'Tue, May 19, 2026, 18:30 UTC',
    });
    assert.equal(r.fixture_identity_guard_status, FIXTURE_IDENTITY_GUARD_PASSED);
});
