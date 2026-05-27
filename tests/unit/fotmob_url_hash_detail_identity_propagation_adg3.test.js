'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const {
    DETAIL_IDENTITY_SOURCE_URL_HASH_FRAGMENT,
    FotMobSourceInventoryAdapter,
    deriveSourceInventoryIdentityEvidence,
    parseSourcePageUrl,
} = require('../../src/infrastructure/services/FotMobSourceInventoryAdapter');
const { resolveRecaptureIdentityContract } = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');
const recapture = require('../../scripts/ops/pageprops_v2_no_write_payload_recapture_execute');
const regeneration = require('../../scripts/ops/pageprops_v2_enriched_target_regeneration_execute');

const BATCH_ID = 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001';

function candidate(index, overrides = {}) {
    const externalId = String(4813735 + index);
    return {
        target_id: `${BATCH_ID}:53_20252026_${externalId}`,
        batch_id: BATCH_ID,
        source: 'fotmob',
        route: 'html_hydration',
        source_inventory_route: 'source_inventory',
        raw_data_version: 'fotmob_pageprops_v2',
        hash_strategy: 'stable_pageprops_payload_v1',
        match_id: `53_20252026_${externalId}`,
        external_id: externalId,
        league_id: 53,
        league_name: 'Ligue 1',
        season: '2025/2026',
        home_team: `Home ${index}`,
        away_team: `Away ${index}`,
        kickoff_time: '2025-08-15T18:45:00.000Z',
        match_date: '2025-08-15T18:45:00.000Z',
        raw_write_ready_for_execution: false,
        ...overrides,
    };
}

function sourceRecord(index, overrides = {}) {
    const base = candidate(index);
    return {
        target_id: base.target_id,
        match_id: base.match_id,
        external_id: base.external_id,
        acquired_source_inventory_record: true,
        source_page_url: `/matches/home-${index}-away-${index}/route-${index}#${base.external_id}`,
        source_page_url_base: `/matches/home-${index}-away-${index}/route-${index}`,
        source_url_fragment_external_id: base.external_id,
        source_slug: `home-${index}-away-${index}`,
        source_route_code: `route-${index}`,
        source_url_path_slug: `route-${index}`,
        schedule_external_id: base.external_id,
        schedule_date: base.kickoff_time,
        schedule_home_team: base.home_team,
        schedule_away_team: base.away_team,
        source_inventory_record_key: `l1_api_data_leagues:overview.leagueOverviewMatches.${index}:${base.external_id}`,
        source_inventory_generated_at: '2026-05-27T15:30:00.000Z',
        identity_evidence_status: 'complete',
        ...overrides,
    };
}

function syntheticManifest(overrides = {}) {
    return {
        batch_id: BATCH_ID,
        candidate_targets: Array.from({ length: 50 }, (_value, index) => candidate(index)),
        next_required_step: 'controlled_enriched_target_regeneration_execution',
        raw_write_ready_for_execution: false,
        accepted_mapping_count: 0,
        phase_5_21_l2v3z_planning_status: 'completed_no_write_enriched_target_regeneration_planning',
        enriched_target_regeneration_planning_status: 'completed_no_write_enriched_target_regeneration_planning',
        ...overrides,
    };
}

function syntheticL2V3YArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3Y',
        candidate_scope_count: 50,
        candidate_targets_matched_count: 50,
        identity_evidence_complete_count: 50,
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
        source_inventory_metadata_records: Array.from({ length: 50 }, (_value, index) => sourceRecord(index)),
        ...overrides,
    };
}

function syntheticL2V3ZArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3Z',
        planned_mapping_key: 'target_id',
        one_to_one_mapping_expected: true,
        duplicate_source_record_key_count: 0,
        duplicate_fragment_external_id_count: 0,
        missing_source_page_url_count: 0,
        missing_source_page_url_base_count: 0,
        missing_source_url_fragment_external_id_count: 0,
        missing_source_inventory_record_key_count: 0,
        regeneration_execution_authorization_required: true,
        no_write_verification_required: true,
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
        ...overrides,
    };
}

test('ADG3 parses FotMob URL hash id and path slug before any HTTP request', () => {
    const parsed = parseSourcePageUrl(
        'https://www.fotmob.com/zh-Hans/matches/manchester-city-vs-afc-bournemouth/2feiv3#4813735'
    );

    assert.equal(
        parsed.source_page_url_base,
        'https://www.fotmob.com/zh-Hans/matches/manchester-city-vs-afc-bournemouth/2feiv3'
    );
    assert.equal(parsed.source_url_fragment_external_id, '4813735');
    assert.equal(parsed.source_slug, 'manchester-city-vs-afc-bournemouth');
    assert.equal(parsed.source_route_code, '2feiv3');
    assert.equal(parsed.source_url_path_slug, '2feiv3');
    assert.equal(/^\d+$/.test(parsed.source_url_fragment_external_id), true);
});

test('ADG3 source inventory seed exposes URL hash as detail identity candidate', () => {
    const evidence = deriveSourceInventoryIdentityEvidence({
        match: {
            id: '4813735',
            pageUrl: '/zh-Hans/matches/manchester-city-vs-afc-bournemouth/2feiv3#4813735',
        },
        sourcePath: 'matches.allMatches.0',
        externalId: '4813735',
        generatedAt: '2026-05-27T15:30:00.000Z',
    });
    const adapter = Object.create(FotMobSourceInventoryAdapter.prototype);
    const seed = adapter.toManifestCandidateSeed(
        {
            external_id: '4813735',
            match_id: '53_20252026_4813735',
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

    assert.equal(seed.source_url_fragment_external_id, '4813735');
    assert.equal(seed.source_url_path_slug, '2feiv3');
    assert.equal(seed.detail_external_id_candidate, '4813735');
    assert.equal(seed.detail_identity_source, DETAIL_IDENTITY_SOURCE_URL_HASH_FRAGMENT);
    assert.equal(seed.raw_write_ready_for_execution, undefined);
});

test('ADG3 regeneration propagates detail identity candidate into active targets without raw-write readiness', () => {
    const result = regeneration.runEnrichedTargetRegenerationExecution({
        manifest: syntheticManifest(),
        l2v3yArtifact: syntheticL2V3YArtifact(),
        l2v3zArtifact: syntheticL2V3ZArtifact(),
        writeFiles: false,
    });
    const target = result.artifact.enriched_targets[0];

    assert.equal(result.ok, true);
    assert.equal(target.source_url_fragment_external_id, '4813735');
    assert.equal(target.source_url_path_slug, 'route-0');
    assert.equal(target.detail_external_id_candidate, '4813735');
    assert.equal(target.detail_identity_source, 'url_hash_fragment');
    assert.equal(target.regeneration_status, 'regenerated_no_write');
    assert.equal(target.raw_write_ready_for_execution, false);
    assert.equal(result.artifact.detail_identity_candidate_count, 50);
    assert.equal(result.artifact.raw_write_ready_for_execution, false);
});

test('ADG3 recapture contract prefers URL hash detail candidate over schedule id but stays blocked until accepted', async () => {
    const target = {
        external_id: '9999999',
        schedule_external_id: '9999999',
        source_page_url: 'https://www.fotmob.com/zh-Hans/matches/manchester-city-vs-afc-bournemouth/2feiv3#4813735',
        source_url_fragment_external_id: '4813735',
        detail_external_id_candidate: '4813735',
        detail_identity_source: 'url_hash_fragment',
    };
    const contract = resolveRecaptureIdentityContract({ target });
    let fetchCalled = false;
    const result = await recapture.recaptureTarget(
        {
            ...target,
            target_id: `${BATCH_ID}:53_20252026_9999999`,
            match_id: '53_20252026_9999999',
            home_team: 'AFC Bournemouth',
            away_team: 'Manchester City',
            kickoff_time: '2026-05-24T15:00:00.000Z',
            baseline_hash: '0'.repeat(64),
        },
        0,
        { timeoutMs: 1000 },
        {
            fetchHtmlFn: async () => {
                fetchCalled = true;
                throw new Error('fetch must remain blocked');
            },
        }
    );

    assert.equal(contract.recapture_expected_identity, '4813735');
    assert.equal(contract.recapture_request_identity, null);
    assert.notEqual(contract.recapture_expected_identity, target.schedule_external_id);
    assert.equal(contract.detail_identity_source, 'url_hash_fragment');
    assert.equal(contract.blockers.includes('missing_accepted_detail_external_id'), true);
    assert.equal(contract.blockers.includes('missing_re_acceptance'), true);
    assert.equal(fetchCalled, false);
    assert.equal(result.identity_contract_blocked, true);
    assert.equal(result.raw_write_execution_ready, false);
});

test('ADG3 accepted detail identity remains the only allowed recapture request identity', () => {
    const contract = resolveRecaptureIdentityContract({
        target: {
            external_id: '9999999',
            schedule_external_id: '9999999',
            source_url_fragment_external_id: '4813735',
            detail_external_id_candidate: '4813735',
            detail_identity_source: 'url_hash_fragment',
            accepted_detail_external_id: '4813735',
            observed_detail_external_id: '4813735',
            current_mapping_effective_status: 'reaccepted',
            current_baseline_effective_status: 'reaccepted',
        },
    });

    assert.equal(contract.recapture_request_allowed, true);
    assert.equal(contract.recapture_request_identity, '4813735');
    assert.equal(contract.recapture_expected_identity, '4813735');
    assert.notEqual(contract.recapture_request_identity, contract.schedule_external_id);
    assert.equal(contract.raw_write_execution_ready, false);
});

test('ADG3 missing hash evidence and suspended mappings remain blocked', () => {
    const missing = resolveRecaptureIdentityContract({
        target: {
            external_id: '4830466',
            schedule_external_id: '4830466',
        },
    });
    const suspended = resolveRecaptureIdentityContract({
        target: {
            external_id: '4830466',
            schedule_external_id: '4830466',
            source_url_fragment_external_id: '4830466',
            detail_external_id_candidate: '4830466',
            detail_identity_source: 'url_hash_fragment',
            current_mapping_effective_status: 'suspended',
            current_baseline_effective_status: 'suspended',
            date_compatibility_status: 'reverse_fixture_detected',
        },
    });

    assert.equal(missing.recapture_request_allowed, false);
    assert.equal(missing.recapture_request_identity, null);
    assert.notEqual(missing.recapture_request_identity, missing.schedule_external_id);
    assert.equal(suspended.recapture_request_allowed, false);
    assert.equal(suspended.blockers.includes('suspended_mapping_or_baseline'), true);
    assert.equal(suspended.blockers.includes('reverse_fixture_detected'), true);
    assert.equal(suspended.raw_write_execution_ready, false);
});
