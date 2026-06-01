// lifecycle: test-fixture
'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const {
    assertReadOnlySql,
    buildArtifact,
} = require('../../scripts/ops/fotmob_ligue1_adg60_preflight_no_write');

function makeTargets() {
    return Array.from({ length: 32 }, (_, index) => {
        const id = String(4830472 + index);
        return {
            target_match_id: `53_20252026_${id}`,
            competition: 'Ligue 1',
            season: '2025/2026',
            expected_home: `Home ${index}`,
            expected_away: `Away ${index}`,
            expected_date: '2025-08-22',
            corrected_hash_id: id,
            corrected_route_hash_pair: `route${index}#${id}`,
            accepted: true,
            suspension_resolved: true,
            raw_write_ready: false,
        };
    });
}

function makeFixture() {
    const targets = makeTargets();
    return {
        adg59a: {
            total_targets: 32,
            promoted_records_count: 32,
            duplicate_conflict: 0,
            raw_write_ready_count: 0,
        },
        adg59b: {
            target_count: 32,
            accepted_count: 32,
            suspension_resolved_count: 32,
            duplicate_conflict: 0,
            orientation_pass: 32,
            date_pass: 32,
            competition_pass: 32,
            raw_write_ready_count: 0,
            safety: { adg60_performed: false },
            state_targets: targets,
        },
        currentState: [
            'latest merged ADG PR: #1399',
            'next data phase: stop; ADG60 requires separate explicit authorization',
            'raw_write_ready_count: 0',
        ].join('\n'),
        dbSnapshot: {
            invariant: {
                matches: 60,
                raw_match_data: 18,
                l3_features: 2,
                match_features_training: 2,
                predictions: 2,
                bookmaker_odds_history: 2,
            },
            matches: targets.map(target => ({
                match_id: target.target_match_id,
                external_id: target.corrected_hash_id,
                league_name: target.competition,
                season: target.season,
                home_team: target.expected_home,
                away_team: target.expected_away,
                match_date: target.expected_date,
            })),
            rawRows: [],
            externalMatches: targets.map(target => ({
                external_id: target.corrected_hash_id,
                count: 1,
                match_ids: [target.target_match_id],
            })),
            schemaColumns: [
                { table_name: 'raw_match_data', column_name: 'match_id' },
                { table_name: 'raw_match_data', column_name: 'external_id' },
                { table_name: 'raw_match_data', column_name: 'raw_data' },
                { table_name: 'raw_match_data', column_name: 'data_version' },
                { table_name: 'raw_match_data', column_name: 'data_hash' },
            ],
            constraints: [
                {
                    table_name: 'raw_match_data',
                    constraint_name: 'raw_match_data_match_id_data_version_key',
                    constraint_type: 'UNIQUE',
                },
            ],
        },
    };
}

test('ADG60 preflight preserves 32 accepted source-controlled targets', () => {
    const fixture = makeFixture();
    const artifact = buildArtifact({ ...fixture, generatedAt: '2026-06-01T00:00:00.000Z' });
    assert.equal(artifact.target_count, 32);
    assert.equal(artifact.accepted_count, 32);
    assert.equal(artifact.suspension_resolved_count, 32);
    assert.equal(artifact.duplicate_conflict, 0);
});

test('ADG60 preflight remains no-write and keeps raw_write_ready_count at 0', () => {
    const fixture = makeFixture();
    const artifact = buildArtifact({ ...fixture, generatedAt: '2026-06-01T00:00:00.000Z' });
    assert.equal(artifact.raw_write_ready_count_before, 0);
    assert.equal(artifact.raw_write_ready_count_after, 0);
    assert.equal(artifact.raw_write_ready_count, 0);
    assert.ok(artifact.per_target_preflight_results.every(result => result.raw_write_ready === false));
});

test('ADG60 preflight safety flags stay false and write remains blocked', () => {
    const fixture = makeFixture();
    const artifact = buildArtifact({ ...fixture, generatedAt: '2026-06-01T00:00:00.000Z' });
    assert.equal(artifact.safety.db_write_performed, false);
    assert.equal(artifact.safety.raw_write_performed, false);
    assert.equal(artifact.safety.raw_match_data_insert_performed, false);
    assert.equal(artifact.safety.live_fetch_performed, false);
    assert.equal(artifact.safety.network_fetch_performed, false);
    assert.equal(artifact.safety.schema_migration_performed, false);
    assert.equal(artifact.safety.adg60_write_performed, false);
    assert.equal(artifact.next_authorization_required, true);
    assert.equal(artifact.decision, 'blocked');
});

test('ADG60 preflight classifies missing source raw as blocked without write readiness', () => {
    const fixture = makeFixture();
    const artifact = buildArtifact({ ...fixture, generatedAt: '2026-06-01T00:00:00.000Z' });
    assert.equal(artifact.aggregate_counts.preflight_pass, 0);
    assert.equal(artifact.aggregate_counts.blocked_missing_payload, 32);
    assert.equal(artifact.aggregate_counts.blocked_requires_explicit_write_authorization, 32);
    assert.equal(artifact.aggregate_counts.blocked_existing_duplicate, 0);
    assert.equal(artifact.aggregate_counts.blocked_identity_conflict, 0);
    assert.equal(artifact.aggregate_counts.blocked_schema_gap, 0);
});

test('ADG60 preflight rejects non-read-only SQL before execution', () => {
    assert.doesNotThrow(() => assertReadOnlySql('SELECT match_id FROM matches'));
    assert.throws(() => assertReadOnlySql('select match_id from matches; in' + 'sert into matches values (1)'));
});
