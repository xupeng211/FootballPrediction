'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const {
    reconcileRouteIdentity,
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
    assert.equal(result.mapping_confidence, 'medium');
    assert.notEqual(result.mapping_confidence, 'high');
    assert.equal(result.raw_write_blocked, true);
    assert.equal(result.safety_blockers.includes('accepted_identity_mapping_missing'), true);
    assert.equal(result.safety_blockers.includes('team_date_status_mismatch'), true);
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
