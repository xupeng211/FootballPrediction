'use strict';

// lifecycle: permanent；GD-A03 runtime behavior / fail-closed / determinism tests。
// 真实 888 离线验证使用同一 assembler，由任务级 external validation 执行。

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const path = require('node:path');
const test = require('node:test');

const featureContract = require('../../config/model_feature_contracts.json').contracts[0];
const {
    buildPriorStateFeatureView,
    normalizeSchedule,
    validatePriorStateOutputFiles,
} = require('../../src/infrastructure/golden_dataset/GdA03PriorStateAssembler');
const { loadFeatureContract } = require('../../scripts/ops/gd_a03_assembler');
const { validatePriorStateArtifact } = require('../../src/infrastructure/golden_dataset/GdA03ArtifactContract');
const {
    FEATURE_CUTOFF_POLICY,
    PRIOR_STATE_LINEAGE_CONTRACT_VERSION,
    REASON_CODES,
    computeBusinessHash,
    stableStringify,
} = require('../../src/infrastructure/golden_dataset/GdA03PriorStateContract');

const REVISION = 'b'.repeat(40);
const HASH = 'a'.repeat(64);

function digest(value) {
    return crypto.createHash('sha256').update(stableStringify(value)).digest('hex');
}

function candidate(id, kickoffAt, homeTeam, awayTeam) {
    return {
        id,
        source_provider: 'FotMob',
        source_match_id: id.split('_').at(-1),
        competition: 'Premier League',
        season: '2024/2025',
        home_team: homeTeam,
        away_team: awayTeam,
        kickoff_at: kickoffAt,
    };
}

function outcome(homeScore, awayScore) {
    return homeScore === awayScore ? 'draw' : homeScore > awayScore ? 'home' : 'away';
}

function fact(row, index) {
    const homeScore = index % 3 === 0 ? 2 : index % 3 === 1 ? 1 : 0;
    const awayScore = index % 3 === 0 ? 0 : index % 3 === 1 ? 1 : 1;
    const homeXg = index + 1;
    const awayXg = index + 2;
    return {
        canonical_match_id: row.id,
        competition: row.competition,
        season: row.season,
        kickoff_at: row.kickoff_at,
        home_team: row.home_team,
        away_team: row.away_team,
        facts: {
            match_result: {
                status: 'AVAILABLE',
                home_score: homeScore,
                away_score: awayScore,
                outcome: outcome(homeScore, awayScore),
                source_path: 'normalized.home_team.score + normalized.away_team.score',
            },
            xg: {
                status: 'VALID',
                source_path: 'normalized.shotmap.shots[*].expectedGoals',
                aggregation: 'sum_known_expectedGoals_by_team_id',
                total_shots: 10,
                shots_with_xg: 10,
                shots_without_xg: 0,
                non_own_goal_shots: 10,
                non_own_goal_shots_with_xg: 10,
                home: { value: homeXg, status: 'COMPLETE', known_shots: 5, missing_shots: 0 },
                away: { value: awayXg, status: 'COMPLETE', known_shots: 5, missing_shots: 0 },
            },
            sections: {},
        },
        provenance: {
            staging: {
                artifact_integrity_sha256: digest(['staging', row.id]),
                business_hash: digest(['business', row.id]),
                stable_payload_sha256: digest(['payload', row.id]),
            },
        },
        source_linkage: {
            status: 'matched',
            matched_id: row.id,
            candidate_ids: [row.id],
        },
    };
}

function buildFixture({ includeSixth = false } = {}) {
    const schedule = [];
    const targets = [];
    const facts = [];
    let sequence = 1;
    const addTarget = (kickoffAt, homeTeam, awayTeam) => {
        const row = candidate(`47_20242025_${String(sequence).padStart(7, '0')}`, kickoffAt, homeTeam, awayTeam);
        sequence += 1;
        schedule.push(row);
        targets.push(row);
        facts.push(fact(row, sequence));
        return row;
    };
    const homeOpponents = ['H1 FC', 'H2 FC', 'H3 FC', 'H4 FC', 'H5 FC', 'H6 FC'];
    const awayOpponents = ['A1 FC', 'A2 FC', 'A3 FC', 'A4 FC', 'A5 FC'];
    const dates = includeSixth
        ? [
              '2024-07-01T12:00:00Z',
              '2024-07-03T12:00:00Z',
              '2024-07-05T12:00:00Z',
              '2024-07-07T12:00:00Z',
              '2024-07-09T12:00:00Z',
              '2024-07-11T12:00:00Z',
          ]
        : [
              '2024-07-03T12:00:00Z',
              '2024-07-05T12:00:00Z',
              '2024-07-07T12:00:00Z',
              '2024-07-09T12:00:00Z',
              '2024-07-11T12:00:00Z',
          ];
    for (let index = 0; index < dates.length; index += 1) addTarget(dates[index], 'Home FC', homeOpponents[index]);
    for (let index = 0; index < awayOpponents.length; index += 1) {
        addTarget(dates[index], awayOpponents[index], 'Away FC');
    }
    const target = addTarget('2024-07-13T12:00:00Z', 'Home FC', 'Away FC');
    const sourceBindings = {
        gd_a01_artifact: { sha256: HASH, business_hash: HASH },
        gd_a02_artifact: { sha256: HASH, business_hash: HASH },
        canonical_schedule: { sha256: HASH, business_hash: HASH },
        feature_contract: { sha256: HASH },
    };
    const options = {
        targetRows: targets.map(row => ({ ...row, canonical_match_id: row.id })),
        factRows: facts,
        scheduleCandidates: schedule,
        scheduleClosure: {
            schema_version: 'canonical-schedule-history/v1',
            status: 'PROVEN',
            authority: 'fixture canonical schedule',
            per_season_expected_counts: { '2024/2025': schedule.length },
        },
        featureContract,
        sourceBindings,
        codeRevision: REVISION,
    };
    return { options, schedule, targets, facts, targetId: target.id };
}

function build(fixture) {
    return buildPriorStateFeatureView(fixture.options);
}

function targetRow(result, targetId) {
    return result.artifact.rows.find(row => row.canonical_match_id === targetId);
}

function assertReject(fn, expectedCode) {
    assert.throws(fn, error => {
        assert.equal(error.code, expectedCode);
        return true;
    });
}

test('GD-A03 derives only strict prior-state values and isolates the target label', () => {
    const fixture = buildFixture();
    const base = build(fixture);
    const target = targetRow(base, fixture.targetId);
    assert.equal(target.feature_cutoff_policy, FEATURE_CUTOFF_POLICY);
    assert.equal(target.features.rolling_xg_home.value, 5);
    assert.equal(target.features.rolling_xg_home.source_match_ids.length, 5);
    assert.equal(target.features.rolling_xg_home.latest_source_kickoff, '2024-07-11T12:00:00Z');
    assert.equal(target.features.rolling_shots_on_target_home.value, null);
    assert.ok(
        target.features.rolling_shots_on_target_home.unavailable_reason_codes.includes(
            REASON_CODES.NO_PROVEN_SOURCE_FACT
        )
    );
    assert.equal(target.features.home_fatigue_index.value, 3 / 7);
    assert.equal(target.target_label.role, 'TRAINING_LABEL_POSTMATCH');
    assert.equal(target.target_label.canonical_match_id, fixture.targetId);
    assert.equal('source_match_id' in target.target_label, false);
    assert.equal(base.artifact.validation_counters.target_match_fact_dependency_count, 0);
    assert.equal(base.artifact.validation_counters.future_match_dependency_count, 0);
    assert.equal(base.artifact.validation_counters.cutoff_violation_count, 0);

    const mutatedFacts = fixture.facts.map(row => ({ ...row, facts: { ...row.facts } }));
    const targetFact = mutatedFacts.find(row => row.canonical_match_id === fixture.targetId);
    targetFact.facts = {
        ...targetFact.facts,
        match_result: { ...targetFact.facts.match_result, home_score: 99, away_score: 0, outcome: 'home' },
        xg: { ...targetFact.facts.xg, home: { ...targetFact.facts.xg.home, value: 9999 } },
    };
    const poisoned = buildPriorStateFeatureView({ ...fixture.options, factRows: mutatedFacts });
    assert.deepEqual(targetRow(poisoned, fixture.targetId).features, target.features);
    assert.notDeepEqual(targetRow(poisoned, fixture.targetId).target_label, target.target_label);
});

test('GD-A03 name/order identity matches config and V26_6_PreMatchAdapter', () => {
    const loaded = loadFeatureContract(path.resolve(__dirname, '../..'));
    assert.deepEqual(loaded.contract.ordered_features, loaded.runtimeFeatureAdapter.orderedFeatures);
    assert.equal(loaded.runtimeFeatureAdapter.symbol, 'V26_6_PreMatchAdapter.V26_6_FEATURES');
});

test('GD-A03 is deterministic across input reorder and ignores future fixtures for earlier targets', () => {
    const fixture = buildFixture();
    const base = build(fixture);
    const reordered = buildPriorStateFeatureView({
        ...fixture.options,
        scheduleCandidates: [...fixture.schedule].reverse(),
        targetRows: [...fixture.options.targetRows].reverse(),
        factRows: [...fixture.facts].reverse(),
    });
    assert.equal(reordered.artifactBytes.toString(), base.artifactBytes.toString());
    assert.equal(reordered.receiptBytes.toString(), base.receiptBytes.toString());

    const future = candidate('47_20242025_9999999', '2024-07-20T12:00:00Z', 'Home FC', 'Future FC');
    const futureOptions = {
        ...fixture.options,
        scheduleCandidates: [...fixture.schedule, future],
        scheduleClosure: {
            ...fixture.options.scheduleClosure,
            per_season_expected_counts: { '2024/2025': fixture.schedule.length + 1 },
        },
    };
    const withFuture = buildPriorStateFeatureView(futureOptions);
    assert.deepEqual(targetRow(withFuture, fixture.targetId).features, targetRow(base, fixture.targetId).features);
});

test('GD-A03 schedule normalization rejects non-canonical IDs and timestamps', () => {
    const fixture = buildFixture();
    const valid = fixture.schedule[0];
    assertReject(
        () => normalizeSchedule([{ ...valid, source_match_id: 'not-numeric' }]),
        'IDENTITY_CONFLICT'
    );
    assertReject(
        () => normalizeSchedule([{ ...valid, kickoff_at: '2024-07-03' }]),
        'FACT_VALUE_INVALID'
    );
});

test('GD-A03 records an actual missing recent match and does not reach farther back', () => {
    const complete = buildFixture({ includeSixth: true });
    const missingId = complete.schedule.find(row => row.kickoff_at === '2024-07-09T12:00:00Z').id;
    const targetId = complete.targetId;
    const options = {
        ...complete.options,
        targetRows: complete.options.targetRows.filter(row => row.canonical_match_id !== missingId),
        factRows: complete.facts.filter(row => row.canonical_match_id !== missingId),
    };
    const result = buildPriorStateFeatureView(options);
    const line = targetRow(result, targetId).features.rolling_xg_home;
    assert.equal(line.value, null);
    assert.equal(line.source_match_ids.length, 5);
    assert.ok(line.source_match_ids.includes(missingId));
    assert.equal(
        line.source_match_ids.includes(complete.schedule.find(row => row.kickoff_at === '2024-07-01T12:00:00Z').id),
        false
    );
    assert.ok(line.unavailable_reason_codes.includes(REASON_CODES.HISTORY_GAP));
    assert.equal(result.artifact.validation_counters.silent_history_gap_count, 0);
});

test('GD-A03 rejects equal/future lineage, identity tamper, and provenance tamper', () => {
    const fixture = buildFixture();
    const result = build(fixture);
    const tampered = JSON.parse(result.artifactBytes.toString('utf8'));
    const target = tampered.rows.find(row => row.canonical_match_id === fixture.targetId);
    target.features.rolling_xg_home.source_identities[0].kickoff_at = target.feature_cutoff_time;
    assertReject(() => validatePriorStateArtifact(tampered), 'CUTOFF_VIOLATION');

    const reversed = buildFixture();
    const scheduleTarget = reversed.options.scheduleCandidates.find(row => row.id === reversed.targetId);
    scheduleTarget.home_team = 'Tampered Home FC';
    assertReject(() => build(reversed), 'IDENTITY_CONFLICT');

    const provenanceTampered = JSON.parse(result.artifactBytes.toString('utf8'));
    const provenanceLine = provenanceTampered.rows.find(row => row.canonical_match_id === fixture.targetId).features
        .rolling_xg_home;
    provenanceLine.provenance_inputs = ['tampered'];
    assertReject(() => validatePriorStateArtifact(provenanceTampered), 'PROVENANCE_INVALID');
});

test('GD-A03 preserves standings history gaps and never estimates position', () => {
    const fixture = buildFixture();
    const target = fixture.options.targetRows.find(row => row.id === fixture.targetId);
    const missingPrior = fixture.schedule.find(
        row => row.kickoff_at === '2024-07-11T12:00:00Z' && row.home_team === 'Home FC'
    );
    const options = {
        ...fixture.options,
        targetRows: fixture.options.targetRows.filter(row => row.canonical_match_id !== missingPrior.id),
        factRows: fixture.facts.filter(row => row.canonical_match_id !== missingPrior.id),
    };
    const result = buildPriorStateFeatureView(options);
    const row = targetRow(result, target.id);
    assert.equal(row.features.home_table_position.value, null);
    assert.ok(
        row.features.home_table_position.unavailable_reason_codes.includes(REASON_CODES.STANDINGS_TIEBREAK_UNPROVEN)
    );
    assert.ok(row.features.home_table_position.unavailable_reason_codes.includes(REASON_CODES.STANDINGS_HISTORY_GAP));
    assert.equal(row.features.home_points.value, null);
});

test('GD-A03 output validation conserves population and rejects tampered business hash', () => {
    const result = build(buildFixture());
    const validated = validatePriorStateOutputFiles(result.artifactBytes, result.receiptBytes);
    assert.equal(validated.artifact.population_accounting.unaccounted_count, 0);
    assert.equal(validated.artifact.population_accounting.duplicate_id_count, 0);
    const tampered = JSON.parse(result.artifactBytes.toString('utf8'));
    tampered.rows[0].features.home_points.value = 12345;
    assertReject(
        () => validatePriorStateOutputFiles(Buffer.from(`${JSON.stringify(tampered)}\n`), result.receiptBytes),
        'BUSINESS_HASH_MISMATCH'
    );
});

test('GD-A03 receipt content hash rejects receipt provenance tampering', () => {
    const result = build(buildFixture());
    const tamperedReceipt = JSON.parse(result.receiptBytes.toString('utf8'));
    tamperedReceipt.code_revision = 'c'.repeat(40);
    assertReject(
        () => validatePriorStateOutputFiles(result.artifactBytes, Buffer.from(`${JSON.stringify(tamperedReceipt)}\n`)),
        'RECEIPT_HASH_MISMATCH'
    );
});

test('GD-A03 runtime source has no DB/network/raw write authority', () => {
    const fs = require('node:fs');
    const path = require('node:path');
    for (const file of [
        path.join(__dirname, '../../src/infrastructure/golden_dataset/GdA03PriorStateContract.js'),
        path.join(__dirname, '../../src/infrastructure/golden_dataset/GdA03PriorStateAssembler.js'),
        path.join(__dirname, '../../scripts/ops/gd_a03_assembler.js'),
    ]) {
        const source = fs.readFileSync(file, 'utf8');
        assert.doesNotMatch(source, /require\(['"](?:pg|ioredis)['"]\)/);
        assert.doesNotMatch(source, /fetch\s*\(/);
        assert.doesNotMatch(source, /raw_match_data/);
        assert.doesNotMatch(source, /require\([^)]*SchemaManager/);
        assert.doesNotMatch(source, /\.(?:connect|query)\s*\(/);
    }
    assert.match(PRIOR_STATE_LINEAGE_CONTRACT_VERSION, /^gd-a03-/);
    assert.equal(
        computeBusinessHash({ x: 1, business_content_sha256: null }),
        computeBusinessHash({ x: 1, business_content_sha256: null })
    );
});
