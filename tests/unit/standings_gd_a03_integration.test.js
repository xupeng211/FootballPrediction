'use strict';

// lifecycle: test-fixture
// 只覆盖适配器的赛程闭合边界、V-next registry binding 和 GD-A03 projection；
// 真实 1,140 场证据验证由 repo 外的离线 audit harness 执行。

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const {
    buildGdA03StandingsProjection,
    GdA03StandingsIntegrationError,
    bindVNextFeatureContract,
    projectStandingsSnapshot,
} = require('../../src/infrastructure/golden_dataset/GdA03StandingsIntegration');
const {
    FrozenEvidenceAdapterError,
    computeEvidenceContentDigest,
    proveCanonicalScheduleClosure,
} = require('../../src/infrastructure/standings/PremierLeagueFrozenEvidenceAdapter');
const {
    STANDINGS_ENGINE_IMPLEMENTATION_BINDING,
} = require('../../src/infrastructure/standings/PointInTimeStandingsEngine');

const REGISTRY = JSON.parse(
    fs.readFileSync(path.resolve(__dirname, '../../config/model_feature_contracts.json'), 'utf8')
);
const SCHEDULE_BUSINESS_HASH = 'eff881728429260012b4de9f93764a08096407e06b9dffd9c9f9e2b4e0bc9d3f';

function expectCode(callback, code) {
    assert.throws(callback, error => error.code === code);
}

function officialFixtureRows() {
    const seasons = ['2022/2023', '2023/2024', '2024/2025'];
    const rows = [];
    for (const season of seasons) {
        const teams = Array.from({ length: 20 }, (_, index) => `PL_TEAM_${season.slice(0, 4)}_${index + 1}`);
        let fixtureNumber = 0;
        for (const homeIndex of teams.keys()) {
            for (const awayIndex of teams.keys()) {
                if (homeIndex === awayIndex) continue;
                const canonicalMatchId = `47_${season.replace('/', '')}_SYNTH_${fixtureNumber}`;
                rows.push({
                    actual_event_time_proven: true,
                    actual_played_kickoff_utc: '2024-01-01T12:00:00.000Z',
                    away_canonical_team_id: teams[awayIndex],
                    away_score: 0,
                    canonical_away_team: teams[awayIndex],
                    canonical_home_team: teams[homeIndex],
                    canonical_match_id: canonicalMatchId,
                    canonical_scheduled_kickoff_utc: '2024-01-01T12:00:00Z',
                    competition: 'Premier League',
                    exception_classification: 'NONE_IN_OFFICIAL_FINAL_FIXTURE_RECORD',
                    home_canonical_team_id: teams[homeIndex],
                    home_score: 0,
                    league_id: '47',
                    official_away_team_name: teams[awayIndex],
                    official_fixture_id: `OFFICIAL_${season}_${fixtureNumber}`,
                    official_fixture_type: 'REGULAR',
                    official_home_team_name: teams[homeIndex],
                    official_opta_fixture_id: `OPTA_${season}_${fixtureNumber}`,
                    official_outcome: 'D',
                    official_phase: 'F',
                    official_provisional_kickoff_utc: '2024-01-01T12:00:00.000Z',
                    official_replay_flag: false,
                    official_status: 'C',
                    result_eligible_for_table: 'YES',
                    result_finality_status: 'OFFICIAL_STATUS_C_PHASE_F_FINAL',
                    season,
                    source_capture_id: `pl-fixtures-${season.replace('/', '-')}`,
                    source_hash: `${String(fixtureNumber + 1).padStart(64, '0')}`,
                    source_record_sha256: `${String(fixtureNumber + 1).padStart(64, '0')}`,
                });
                fixtureNumber += 1;
            }
        }
    }
    return rows;
}

function validScheduleDocument(rows) {
    return {
        schema_version: 'standings-official-fixture-projection/v1',
        scope: {
            competition: 'Premier League',
            league_id: '47',
            seasons: ['2022/2023', '2023/2024', '2024/2025'],
            canonical_schedule_count: 1140,
            canonical_schedule_sha256: 'a'.repeat(64),
            canonical_required_set_sha256: 'b'.repeat(64),
            canonical_schedule_business_sha256: SCHEDULE_BUSINESS_HASH,
        },
        rows,
    };
}

function projectionContext() {
    return {
        sourceBindings: {
            exception_status_audit: { sha256: 'c'.repeat(64) },
            postponed_rescheduled_audit: { sha256: 'd'.repeat(64) },
        },
        lineage: {
            targetByMatchId: {
                target: {
                    evidence_file: 'target-closure-audit.json',
                    target_status: 'EVIDENCE_READY',
                    target_reason_codes: [],
                    target_kickoff_utc: '2024-01-01T12:00:00.000Z',
                },
            },
            resultByMatchId: {
                result: {
                    source_record_sha256: 'e'.repeat(64),
                    source_hash: 'f'.repeat(64),
                    actual_event_time_utc: '2023-12-31T12:00:00.000Z',
                    evidence_file: 'normalized-prior-result-ledger.json',
                },
            },
            adjustmentById: {},
        },
    };
}

function validScheduleClosure() {
    return {
        status: 'PROVEN',
        canonical_schedule_count: 1140,
        canonical_schedule_sha256: 'a'.repeat(64),
        canonical_required_set_sha256: 'b'.repeat(64),
        canonical_schedule_business_sha256: SCHEDULE_BUSINESS_HASH,
        source_binding: { sha256: '1'.repeat(64) },
    };
}

function validEngineOutput(overrides = {}) {
    return {
        snapshot_status: 'AVAILABLE',
        target_match_id: 'target',
        target_kickoff_utc: '2024-01-01T12:00:00.000Z',
        season: '2023/2024',
        contract_id: 'standings/premier-league-point-in-time/v1',
        contract_version: 'v1',
        home_table_position: 4,
        away_table_position: 7,
        table_position_diff: -3,
        unavailable_reason_codes: [],
        source_event_ids_used: ['result'],
        administrative_adjustment_ids_considered: [],
        administrative_adjustment_ids_applied: [],
        input_digest: '2'.repeat(64),
        provenance_digest: '3'.repeat(64),
        ...overrides,
    };
}

test('canonical schedule closure proves 1,140 fixtures and 20-club 19/19 closure', () => {
    const rows = officialFixtureRows();
    const closure = proveCanonicalScheduleClosure(validScheduleDocument(rows), {
        sha256: '4'.repeat(64),
        schema_version: 'standings-official-fixture-projection/v1',
    });
    assert.equal(rows.length, 1140);
    assert.equal(closure.status, 'PROVEN');
    assert.deepEqual(
        Object.fromEntries(
            Object.entries(closure.per_season).map(([season, value]) => [season, value.canonical_fixtures])
        ),
        { '2022/2023': 380, '2023/2024': 380, '2024/2025': 380 }
    );
    for (const value of Object.values(closure.per_season)) {
        assert.equal(value.team_count, 20);
        assert.equal(value.fixtures_per_team, 38);
        assert.equal(value.home_fixtures_per_team, 19);
        assert.equal(value.away_fixtures_per_team, 19);
    }
});

test('schedule closure fails closed on missing, duplicate, or conflicting fixture identity', () => {
    const rows = officialFixtureRows();
    expectCode(
        () =>
            proveCanonicalScheduleClosure(validScheduleDocument(rows.slice(1)), {
                sha256: '4'.repeat(64),
                schema_version: 'v1',
            }),
        'DEPENDENCY_UNAVAILABLE'
    );
    const duplicate = [...rows];
    duplicate[1] = { ...duplicate[1], canonical_match_id: duplicate[0].canonical_match_id };
    expectCode(
        () =>
            proveCanonicalScheduleClosure(validScheduleDocument(duplicate), {
                sha256: '4'.repeat(64),
                schema_version: 'v1',
            }),
        'RESULT_IDENTITY_CONFLICT'
    );
    const conflict = [...rows];
    conflict[0] = { ...conflict[0], home_canonical_team_id: conflict[0].away_canonical_team_id };
    expectCode(
        () =>
            proveCanonicalScheduleClosure(validScheduleDocument(conflict), {
                sha256: '4'.repeat(64),
                schema_version: 'v1',
            }),
        'RESULT_IDENTITY_CONFLICT'
    );
});

test('normalized evidence content digest is permutation invariant but changes on tamper', () => {
    const document = { rows: [{ id: 'b' }, { id: 'a' }], scope: { seasons: ['2023/2024', '2022/2023'] } };
    const permuted = { rows: [...document.rows].reverse(), scope: { seasons: [...document.scope.seasons].reverse() } };
    assert.equal(computeEvidenceContentDigest(document), computeEvidenceContentDigest(permuted));
    assert.notEqual(
        computeEvidenceContentDigest(document),
        computeEvidenceContentDigest({ ...document, rows: [{ id: 'tampered' }, { id: 'a' }] })
    );
});

test('V-next binding comes from the canonical registry and rejects order/activation drift', () => {
    const binding = bindVNextFeatureContract(REGISTRY);
    assert.equal(binding.contract_id, 'canonical_prematch/vnext-v1');
    assert.equal(binding.feature_count, 17);
    assert.equal(binding.activation_status, 'DEFINED_NOT_ACTIVATED');
    const wrongOrder = JSON.parse(JSON.stringify(REGISTRY));
    const vnext = wrongOrder.contracts.find(contract => contract.contract_id === 'canonical_prematch/vnext-v1');
    [vnext.ordered_features[0], vnext.ordered_features[1]] = [vnext.ordered_features[1], vnext.ordered_features[0]];
    expectCode(() => bindVNextFeatureContract(wrongOrder), 'RULE_VERSION_UNPROVEN');
    const activated = JSON.parse(JSON.stringify(REGISTRY));
    activated.contracts.find(contract => contract.contract_id === 'canonical_prematch/vnext-v1').activation_status =
        'ACTIVE_DEFAULT';
    expectCode(() => bindVNextFeatureContract(activated), 'RULE_VERSION_UNPROVEN');
});

test('GD-A03 projection copies engine values and computes no independent standings semantics', () => {
    const row = projectStandingsSnapshot({
        output: validEngineOutput(),
        vNextContractBinding: bindVNextFeatureContract(REGISTRY),
        context: projectionContext(),
        scheduleClosure: validScheduleClosure(),
    });
    assert.equal(row.home_table_position, 4);
    assert.equal(row.away_table_position, 7);
    assert.equal(row.table_position_diff, -3);
    assert.equal(row.feature_lines.home_table_position.value, 4);
    assert.equal(row.feature_lines.table_position_diff.value, -3);
    assert.equal(row.v_next_activation_status, 'DEFINED_NOT_ACTIVATED');
    assert.deepEqual(
        row.feature_lines.home_table_position.engine_implementation,
        STANDINGS_ENGINE_IMPLEMENTATION_BINDING
    );
    assert.equal(Object.hasOwn(row.feature_lines.home_table_position.engine_implementation, 'source_commit'), false);
});

test('GD-A03 projection keeps all standings values null when engine is unavailable', () => {
    const row = projectStandingsSnapshot({
        output: validEngineOutput({
            snapshot_status: 'UNAVAILABLE',
            home_table_position: null,
            away_table_position: null,
            table_position_diff: null,
            unavailable_reason_codes: ['ADMIN_ADJUSTMENT_EFFECTIVE_TIME_AMBIGUOUS'],
            source_event_ids_used: [],
        }),
        vNextContractBinding: bindVNextFeatureContract(REGISTRY),
        context: projectionContext(),
        scheduleClosure: validScheduleClosure(),
    });
    assert.equal(row.home_table_position, null);
    assert.equal(row.away_table_position, null);
    assert.equal(row.table_position_diff, null);
    assert.equal(row.feature_lines.home_table_position.value, null);
    assert.deepEqual(row.unavailable_reason_codes, ['ADMIN_ADJUSTMENT_EFFECTIVE_TIME_AMBIGUOUS']);
});

test('GD-A03 projection rejects wrong diff orientation and fabricated unavailable value', () => {
    const args = {
        vNextContractBinding: bindVNextFeatureContract(REGISTRY),
        context: projectionContext(),
        scheduleClosure: validScheduleClosure(),
    };
    expectCode(
        () => projectStandingsSnapshot({ ...args, output: validEngineOutput({ table_position_diff: 3 }) }),
        'STANDINGS_POSITION_UNAVAILABLE'
    );
    expectCode(
        () =>
            projectStandingsSnapshot({
                ...args,
                output: validEngineOutput({
                    snapshot_status: 'UNAVAILABLE',
                    home_table_position: 1,
                    away_table_position: null,
                    table_position_diff: null,
                    unavailable_reason_codes: ['DEPENDENCY_UNAVAILABLE'],
                    source_event_ids_used: [],
                }),
            }),
        'STANDINGS_POSITION_UNAVAILABLE'
    );
});

test('GD-A03 projection rejects caller-supplied engine provenance, including a fake valid SHA', () => {
    const args = {
        output: validEngineOutput(),
        vNextContractBinding: bindVNextFeatureContract(REGISTRY),
        context: projectionContext(),
        scheduleClosure: validScheduleClosure(),
        engineImplementation: {
            implementation_id: 'PointInTimeStandingsEngine',
            source_commit: '9999999999999999999999999999999999999999',
        },
    };
    expectCode(() => projectStandingsSnapshot(args), 'DEPENDENCY_UNAVAILABLE');
});

test('GD-A03 projection rejects malformed caller-supplied source provenance', () => {
    const args = {
        output: validEngineOutput(),
        vNextContractBinding: bindVNextFeatureContract(REGISTRY),
        context: projectionContext(),
        scheduleClosure: validScheduleClosure(),
        engineImplementation: { implementation_id: 'PointInTimeStandingsEngine', source_commit: '9c50ab1' },
    };
    expectCode(() => projectStandingsSnapshot(args), 'DEPENDENCY_UNAVAILABLE');
});

test('the integration surface remains separate from V1 assembler module', () => {
    assert.equal(typeof buildGdA03StandingsProjection, 'function');
    assert.equal(GdA03StandingsIntegrationError.prototype.name, 'Error');
    const v1Source = fs.readFileSync(
        path.resolve(__dirname, '../../src/infrastructure/golden_dataset/GdA03PriorStateAssembler.js'),
        'utf8'
    );
    assert.match(v1Source, /function buildTablePositionLine/);
    assert.match(v1Source, /STANDINGS_HISTORY_GAP/);
});

test('integration module does not expose filesystem/network/db dependencies', () => {
    const integrationSource = fs.readFileSync(
        path.resolve(__dirname, '../../src/infrastructure/golden_dataset/GdA03StandingsIntegration.js'),
        'utf8'
    );
    const adapterSource = fs.readFileSync(
        path.resolve(__dirname, '../../src/infrastructure/standings/PremierLeagueFrozenEvidenceAdapter.js'),
        'utf8'
    );
    for (const source of [integrationSource, adapterSource]) {
        assert.doesNotMatch(source, /require\(['"]node:(?:fs|http|https|net|tls|dgram|child_process)['"]\)/);
        assert.doesNotMatch(source, /process\.env/);
        assert.doesNotMatch(source, /fetch\s*\(/);
        assert.doesNotMatch(source, /SELECT\s+/i);
    }
    assert.equal(FrozenEvidenceAdapterError.prototype.name, 'Error');
});
