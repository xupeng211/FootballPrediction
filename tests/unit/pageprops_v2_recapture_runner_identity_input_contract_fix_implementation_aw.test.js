'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const recapture = require('../../scripts/ops/pageprops_v2_no_write_payload_recapture_execute');
const { resolveRecaptureIdentityContract } = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

function pagePropsFor(detailExternalId = '4830759', overrides = {}) {
    return {
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
        ...overrides,
    };
}

function htmlFor(pageProps) {
    return `<html><head><script id="__NEXT_DATA__" type="application/json">${JSON.stringify({
        props: { pageProps },
    })}</script></head><body>fixture</body></html>`;
}

function reacceptedTarget(overrides = {}) {
    const detailExternalId = overrides.accepted_detail_external_id || '4830759';
    const pageProps = pagePropsFor(detailExternalId);
    return {
        target_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001:53_20252026_4830466',
        match_id: '53_20252026_4830466',
        external_id: '4830466',
        schedule_external_id: '4830466',
        source_page_url: `/match/${detailExternalId}#${detailExternalId}`,
        source_page_url_base: `/match/${detailExternalId}`,
        source_url_fragment_external_id: detailExternalId,
        accepted_detail_external_id: detailExternalId,
        current_mapping_effective_status: 'reaccepted',
        current_baseline_effective_status: 'reaccepted',
        re_acceptance_execution_performed: true,
        home_team: 'Rennes',
        away_team: 'Marseille',
        kickoff_time: '2026-05-17T19:00:00.000Z',
        match_date: '2026-05-17T19:00:00.000Z',
        status: 'finished',
        baseline_hash: recapture.computeStablePagePropsHash(pageProps),
        ...overrides,
    };
}

test('L2V3AW resolver blocks schedule_external_id-only detail route identity', () => {
    const contract = resolveRecaptureIdentityContract({
        target: {
            external_id: '4830466',
            schedule_external_id: '4830466',
            source_page_url_base: '/match/4830466',
            source_url_fragment_external_id: '4830466',
        },
    });

    assert.equal(contract.recapture_request_allowed, false);
    assert.equal(contract.recapture_request_identity, null);
    assert.equal(contract.schedule_external_id, '4830466');
    assert.equal(contract.route_identity_strategy, 'blocked_until_reaccepted_identity_contract');
    assert.equal(contract.canonical_identity_source, 'none_until_reaccepted_mapping_baseline');
    assert.equal(contract.blockers.includes('missing_accepted_detail_external_id'), true);
    assert.equal(contract.blockers.includes('missing_re_acceptance'), true);
    assert.equal(contract.blockers.includes('page_url_base_alone_insufficient'), true);
    assert.equal(contract.raw_write_execution_ready, false);
});

test('L2V3AW recapture runner uses accepted detail identity, not schedule_external_id, when reaccepted', async () => {
    const target = reacceptedTarget();
    let requestedUrl = null;
    const result = await recapture.recaptureTarget(
        target,
        0,
        { timeoutMs: 1000 },
        {
            fetchHtmlFn: async url => {
                requestedUrl = url;
                const body = htmlFor(pagePropsFor('4830759'));
                return {
                    ok: true,
                    request_url: url,
                    final_url: url,
                    http_status: 200,
                    body_byte_length: Buffer.byteLength(body, 'utf8'),
                    body,
                };
            },
        }
    );

    assert.equal(requestedUrl, 'https://www.fotmob.com/match/4830759');
    assert.equal(result.target_status, 'recapture_succeeded');
    assert.equal(result.schedule_external_id, '4830466');
    assert.equal(result.recapture_request_identity, '4830759');
    assert.equal(result.recapture_expected_identity, '4830759');
    assert.equal(result.route_identity_strategy, 'accepted_detail_external_id');
    assert.equal(result.identity_match_status, 'match');
    assert.equal(result.raw_write_execution_ready, false);
    assert.equal(result.baseline_update_allowed, false);
});

test('L2V3AW suspended mapping or baseline blocks recapture without calling fetch', async () => {
    const target = reacceptedTarget({
        current_mapping_effective_status: 'suspended',
        current_baseline_effective_status: 'suspended',
        re_acceptance_execution_performed: false,
    });
    let fetchCalled = false;
    const result = await recapture.recaptureTarget(
        target,
        0,
        { timeoutMs: 1000 },
        {
            fetchHtmlFn: async () => {
                fetchCalled = true;
                throw new Error('fetch must not be called');
            },
        }
    );

    assert.equal(fetchCalled, false);
    assert.equal(result.identity_contract_blocked, true);
    assert.equal(result.stopping_rule_triggered, 'identity_contract_blocked');
    assert.equal(result.blocker_list.includes('suspended_mapping_or_baseline'), true);
    assert.equal(result.blocker_list.includes('missing_re_acceptance'), true);
    assert.equal(result.recapture_request_identity, null);
});

test('L2V3AW missing re-acceptance blocks recapture and does not fall back to schedule route', async () => {
    const target = reacceptedTarget({
        current_mapping_effective_status: 'suspended',
        current_baseline_effective_status: 'suspended',
        re_acceptance_execution_performed: false,
    });
    const contract = resolveRecaptureIdentityContract({ target });

    assert.equal(contract.recapture_request_allowed, false);
    assert.equal(contract.recapture_request_identity, null);
    assert.equal(contract.blockers.includes('missing_re_acceptance'), true);
    assert.notEqual(contract.recapture_request_identity, target.schedule_external_id);
});

test('L2V3AW page_url_base, slug, and fragment alone remain insufficient', () => {
    const contract = resolveRecaptureIdentityContract({
        target: {
            external_id: '4830466',
            schedule_external_id: '4830466',
            source_page_url: '/matches/rennes-vs-marseille/2t9n7h#4830466',
            source_page_url_base: '/matches/rennes-vs-marseille/2t9n7h',
            source_url_fragment_external_id: '4830466',
            current_mapping_effective_status: 'accepted',
            current_baseline_effective_status: 'accepted',
        },
    });

    assert.equal(contract.recapture_request_allowed, false);
    assert.equal(contract.page_url_base_alone_insufficient_enforced, true);
    assert.equal(contract.blockers.includes('page_url_base_alone_insufficient'), true);
    assert.equal(contract.raw_write_execution_ready, false);
});

test('L2V3AW requested 4830466 observed 4830759 mismatch remains blocking and hash is secondary', () => {
    const contract = resolveRecaptureIdentityContract({
        target: {
            external_id: '4830466',
            schedule_external_id: '4830466',
            accepted_detail_external_id: '4830466',
            observed_detail_external_id: '4830759',
            current_mapping_effective_status: 'reaccepted',
            current_baseline_effective_status: 'reaccepted',
            re_acceptance_execution_performed: true,
            date_compatibility_status: 'reverse_fixture_detected',
            hash_validation_status: 'hash_mismatch',
            hash_matches_baseline: false,
        },
    });

    assert.equal(contract.recapture_request_allowed, false);
    assert.equal(contract.blockers.includes('identity_mismatch'), true);
    assert.equal(contract.blockers.includes('reverse_fixture_detected'), true);
    assert.equal(contract.blockers.includes('hash_mismatch_secondary_to_identity_mismatch'), true);
    assert.equal(contract.hash_validation_status, 'secondary_to_identity_mismatch');
    assert.equal(contract.baseline_update_allowed, false);
    assert.equal(contract.baseline_re_acceptance_allowed, false);
    assert.equal(contract.raw_write_execution_ready, false);
});
