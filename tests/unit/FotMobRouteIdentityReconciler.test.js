'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const {
    reconcileRouteIdentity,
    evaluateDateCompatibility,
    assertRawWriteIdentityGate,
} = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

function target(overrides = {}) {
    return {
        external_id: '4830466',
        home_team: 'Rennes',
        away_team: 'Marseille',
        match_date: '2025-08-15T18:45:00.000Z',
        status: 'finished',
        page_url_base: '/matches/rennes-vs-marseille/2t9n7h',
        ...overrides,
    };
}

function pageProps(overrides = {}) {
    return {
        general: {
            matchId: '4830759',
            homeTeam: { name: 'Rennes' },
            awayTeam: { name: 'Marseille' },
            matchTimeUTC: '2025-08-16T18:45:00.000Z',
            status: 'finished',
            pageUrl: '/matches/rennes-vs-marseille/2t9n7h#4830759',
        },
        header: { teams: [{ name: 'Rennes' }, { name: 'Marseille' }] },
        ...overrides,
    };
}

test('requested schedule id equals observed detail id is identity_match', () => {
    const result = reconcileRouteIdentity({
        target: target({ external_id: '4830747', page_url_base: '/matches/home-vs-away/abc' }),
        pageProps: pageProps({
            general: {
                matchId: '4830747',
                homeTeam: { name: 'Rennes' },
                awayTeam: { name: 'Marseille' },
                matchTimeUTC: '2025-08-15T18:45:00.000Z',
                status: 'finished',
                pageUrl: '/matches/home-vs-away/abc#4830747',
            },
        }),
    });

    assert.equal(result.requested_schedule_external_id, '4830747');
    assert.equal(result.observed_detail_external_id, '4830747');
    assert.equal(result.canonical_identity_status, 'identity_match');
    assert.equal(result.identity_reconciliation_status, 'identity_match');
    assert.equal(result.raw_write_blocked, false);
});

test('identity match with unknown date status still blocks raw write', () => {
    const result = reconcileRouteIdentity({
        target: target({ external_id: '4830747', match_date: null, page_url_base: '/matches/home-vs-away/abc' }),
        pageProps: pageProps({
            general: {
                matchId: '4830747',
                homeTeam: { name: 'Rennes' },
                awayTeam: { name: 'Marseille' },
                status: 'finished',
                pageUrl: '/matches/home-vs-away/abc#4830747',
            },
        }),
    });
    const gate = assertRawWriteIdentityGate(result);

    assert.equal(result.canonical_identity_status, 'identity_match');
    assert.equal(result.date_compatibility_status, 'unknown');
    assert.equal(result.date_compatibility_blocks_raw_write, true);
    assert.equal(result.raw_write_blocked, true);
    assert.equal(result.safety_blockers.includes('unknown'), true);
    assert.equal(gate.ok, false);
    assert.equal(gate.transaction_began, false);
});

test('pageUrl base match plus date mismatch remains unresolved and not high confidence', () => {
    const result = reconcileRouteIdentity({ target: target(), pageProps: pageProps() });

    assert.equal(result.requested_schedule_external_id, '4830466');
    assert.equal(result.observed_detail_external_id, '4830759');
    assert.equal(result.page_url_base_match_status, 'match');
    assert.equal(result.team_date_status_match_status, 'date_mismatch');
    assert.equal(
        result.schedule_external_id_vs_detail_external_id_status,
        'requested_vs_observed_external_id_mismatch'
    );
    assert.equal(result.identity_reconciliation_status, 'unresolved_schedule_detail_mapping');
    assert.equal(result.date_compatibility_status, 'unknown');
    assert.equal(result.mapping_confidence, 'blocked');
    assert.notEqual(result.mapping_confidence, 'high');
    assert.equal(result.raw_write_blocked, true);
    assert.equal(result.safety_blockers.includes('accepted_identity_mapping_missing'), true);
    assert.equal(result.safety_blockers.includes('team_date_status_mismatch'), true);
    assert.equal(result.safety_blockers.includes('page_url_base_alone_insufficient_for_acceptance'), true);
});

test('proposal-only mapping is not accepted and blocks raw write', () => {
    const result = reconcileRouteIdentity({
        target: target(),
        pageProps: pageProps(),
        proposalOnlyMapping: true,
        acceptedIdentityMappingPresent: false,
    });
    const gate = assertRawWriteIdentityGate(result);

    assert.equal(result.proposal_mapping_used_for_raw_write, false);
    assert.equal(result.safety_blockers.includes('proposal_only_mapping_not_accepted'), true);
    assert.equal(gate.ok, false);
    assert.equal(gate.blocked_reason, 'ROUTE_IDENTITY_GATE_BLOCKED');
    assert.equal(gate.transaction_began, false);
    assert.equal(gate.inserted_raw_match_data_count, 0);
});

test('multiple detail ids or schedule ids block acceptance', () => {
    const result = reconcileRouteIdentity({
        target: target(),
        pageProps: pageProps(),
        multipleDetailIdsForSameScheduleId: true,
        multipleScheduleIdsForSameDetailId: true,
    });

    assert.equal(result.raw_write_blocked, true);
    assert.equal(result.safety_blockers.includes('multiple_detail_ids_for_same_schedule_id'), true);
    assert.equal(result.safety_blockers.includes('multiple_schedule_ids_for_same_detail_id'), true);
});

test('date rule engine classifies exact date match', () => {
    const result = evaluateDateCompatibility({
        requestedMatchDate: '2025-08-15T18:45:00.000Z',
        observedMatchDate: '2025-08-15T18:45:00.000Z',
    });

    assert.equal(result.date_compatibility_status, 'date_match');
    assert.equal(result.positive_evidence, true);
    assert.equal(result.blocks_raw_write, false);
});

test('date rule engine classifies same UTC day and timezone-only mismatch', () => {
    const sameDay = evaluateDateCompatibility({
        requestedMatchDate: '2025-08-15T18:45:00.000Z',
        observedMatchDate: '2025-08-15T21:45:00.000Z',
    });
    const timezoneOnly = evaluateDateCompatibility({
        requestedMatchDate: '2025-08-15T23:30:00-02:00',
        observedMatchDate: '2025-08-16T01:30:00.000Z',
    });

    assert.equal(sameDay.date_compatibility_status, 'same_utc_day');
    assert.equal(sameDay.positive_evidence, true);
    assert.equal(timezoneOnly.date_compatibility_status, 'timezone_only_mismatch');
    assert.equal(timezoneOnly.review_required, true);
    assert.equal(timezoneOnly.blocks_raw_write, false);
});

test('large date gap plus reversed teams and same pageUrl is reverse_fixture_detected', () => {
    const result = reconcileRouteIdentity({
        target: target({
            external_id: '4830466',
            home_team: 'Rennes',
            away_team: 'Marseille',
            match_date: '2025-08-15T18:45:00.000Z',
            page_url_base: '/matches/marseille-vs-rennes/2t9n7h',
        }),
        pageProps: pageProps({
            general: {
                matchId: '4830759',
                homeTeam: { name: 'Marseille' },
                awayTeam: { name: 'Rennes' },
                matchTimeUTC: '2026-05-17T19:00:00.000Z',
                status: 'finished',
                pageUrl: '/matches/marseille-vs-rennes/2t9n7h#4830759',
            },
        }),
        acceptedIdentityMappingPresent: true,
    });
    const gate = assertRawWriteIdentityGate(result);

    assert.equal(result.date_compatibility_status, 'reverse_fixture_detected');
    assert.equal(result.reverse_fixture_detected, true);
    assert.equal(result.date_compatibility_blocks_raw_write, true);
    assert.equal(result.date_compatibility_blocks_identity_mapping_acceptance, true);
    assert.equal(result.raw_write_blocked, true);
    assert.equal(result.safety_blockers.includes('reverse_fixture_detected'), true);
    assert.equal(gate.ok, false);
    assert.equal(gate.transaction_began, false);
    assert.equal(gate.inserted_raw_match_data_count, 0);
});

test('large unexplained date gap blocks as unresolved_large_gap', () => {
    const result = reconcileRouteIdentity({
        target: target({ match_date: '2025-08-15T18:45:00.000Z' }),
        pageProps: pageProps({
            general: {
                matchId: '4830759',
                homeTeam: { name: 'Rennes' },
                awayTeam: { name: 'Marseille' },
                matchTimeUTC: '2026-01-17T18:00:00.000Z',
                status: 'finished',
                pageUrl: '/matches/rennes-vs-marseille/2t9n7h#4830759',
            },
        }),
        acceptedIdentityMappingPresent: true,
    });
    const gate = assertRawWriteIdentityGate(result);

    assert.equal(result.date_compatibility_status, 'unresolved_large_gap');
    assert.equal(result.raw_write_blocked, true);
    assert.equal(result.safety_blockers.includes('unresolved_large_gap'), true);
    assert.equal(gate.ok, false);
});

test('cross-season slug reuse blocks raw write', () => {
    const result = reconcileRouteIdentity({
        requestedScheduleExternalId: '4830466',
        requestedPageUrlBase: '/matches/a-vs-b/reused',
        requestedHomeTeam: 'A',
        requestedAwayTeam: 'B',
        requestedMatchDate: '2025-05-17T18:00:00.000Z',
        requestedSeason: '2024/2025',
        observedDetailExternalId: '5830466',
        observedPageUrlBase: '/matches/a-vs-b/reused',
        observedHomeTeam: 'A',
        observedAwayTeam: 'B',
        observedMatchDate: '2025-08-17T18:00:00.000Z',
        observedSeason: '2025/2026',
        acceptedIdentityMappingPresent: true,
    });

    assert.equal(result.date_compatibility_status, 'cross_season_slug_reuse');
    assert.equal(result.raw_write_blocked, true);
    assert.equal(result.safety_blockers.includes('cross_season_slug_reuse'), true);
});

test('missing or invalid dates classify as unknown and block mismatched route writes', () => {
    const missing = reconcileRouteIdentity({
        target: target({ match_date: null }),
        pageProps: pageProps({
            general: {
                matchId: '4830759',
                homeTeam: { name: 'Rennes' },
                awayTeam: { name: 'Marseille' },
                status: 'finished',
                pageUrl: '/matches/rennes-vs-marseille/2t9n7h#4830759',
            },
        }),
        acceptedIdentityMappingPresent: true,
    });
    const invalid = evaluateDateCompatibility({
        requestedMatchDate: 'not-a-date',
        observedMatchDate: '2025-08-15T18:45:00.000Z',
    });

    assert.equal(missing.date_compatibility_status, 'unknown');
    assert.equal(missing.raw_write_blocked, true);
    assert.equal(missing.safety_blockers.includes('unknown'), true);
    assert.equal(invalid.date_compatibility_status, 'unknown');
    assert.equal(invalid.requested_date_error, 'invalid');
});

test('postponed or rescheduled date mismatch requires explicit evidence and review', () => {
    const result = evaluateDateCompatibility({
        requestedMatchDate: '2025-08-15T18:45:00.000Z',
        observedMatchDate: '2025-08-20T18:45:00.000Z',
        rescheduleEvidence: 'explicit postponed match notice reviewed',
    });

    assert.equal(result.date_compatibility_status, 'postponed_or_rescheduled_explained');
    assert.equal(result.review_required, true);
    assert.equal(result.blocks_raw_write, false);
});
