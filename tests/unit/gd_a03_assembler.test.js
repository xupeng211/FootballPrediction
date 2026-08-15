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
    validateScheduleClosure,
    validatePriorStateOutputFiles,
} = require('../../src/infrastructure/golden_dataset/GdA03PriorStateAssembler');
const { loadFeatureContract } = require('../../scripts/ops/gd_a03_assembler');
const { validatePriorStateArtifact } = require('../../src/infrastructure/golden_dataset/GdA03ArtifactContract');
const {
    FEATURE_CUTOFF_POLICY,
    PRIOR_STATE_LINEAGE_CONTRACT_VERSION,
    REASON_CODES,
    SCHEDULE_TEAM_CLOSURE_SCHEMA_VERSION,
    computeBusinessHash,
    stableStringify,
} = require('../../src/infrastructure/golden_dataset/GdA03PriorStateContract');

const REVISION = 'b'.repeat(40);
const HASH = 'a'.repeat(64);

function digest(value) {
    return crypto.createHash('sha256').update(stableStringify(value)).digest('hex');
}

function teamClosure(schedule) {
    const perTeamCounts = {};
    for (const row of schedule) {
        const seasonTeams = perTeamCounts[row.season] || {};
        const home = seasonTeams[row.home_team] || { total: 0, home: 0, away: 0 };
        const away = seasonTeams[row.away_team] || { total: 0, home: 0, away: 0 };
        home.total += 1;
        home.home += 1;
        away.total += 1;
        away.away += 1;
        seasonTeams[row.home_team] = home;
        seasonTeams[row.away_team] = away;
        perTeamCounts[row.season] = seasonTeams;
    }
    return {
        schema_version: SCHEDULE_TEAM_CLOSURE_SCHEMA_VERSION,
        status: 'PROVEN',
        teams_per_season: 20,
        fixtures_per_team: 38,
        home_fixtures_per_team: 19,
        away_fixtures_per_team: 19,
        per_team_counts: perTeamCounts,
    };
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
            shots_on_target: {
                status: 'UNAVAILABLE',
                source_path: 'normalized.shotmap.shots[*].isOnTarget',
                aggregation: 'count_true_isOnTarget_by_team_id',
                total_shots: null,
                shots_with_on_target: null,
                shots_without_on_target: null,
                home: { value: null, status: 'UNAVAILABLE', known_shots: 0, missing_shots: 0 },
                away: { value: null, status: 'UNAVAILABLE', known_shots: 0, missing_shots: 0 },
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

function completeShotsOnTarget(home, away) {
    return {
        status: 'VALID',
        source_path: 'normalized.shotmap.shots[*].isOnTarget',
        aggregation: 'count_true_isOnTarget_by_team_id',
        total_shots: home + away + 2,
        shots_with_on_target: home + away,
        shots_without_on_target: 0,
        home: { value: home, status: 'COMPLETE', known_shots: home + 1, missing_shots: 0 },
        away: { value: away, status: 'COMPLETE', known_shots: away + 1, missing_shots: 0 },
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
    const canonicalTeams = ['Home FC', 'Away FC', ...Array.from({ length: 18 }, (_, index) => `Team ${index + 3}`)];
    const homeOpponents = canonicalTeams.slice(2, 2 + (includeSixth ? 6 : 5));
    const awayOpponents = canonicalTeams.slice(8, 13);
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
    const existingPairs = new Set(schedule.map(row => `${row.home_team}\u0000${row.away_team}`));
    let fillerIndex = 0;
    let futureSlot = null;
    for (const homeTeam of canonicalTeams) {
        for (const awayTeam of canonicalTeams) {
            if (homeTeam === awayTeam || existingPairs.has(`${homeTeam}\u0000${awayTeam}`)) continue;
            const filler = candidate(
                `47_20242025_${String(sequence).padStart(7, '0')}`,
                new Date(Date.parse('2024-08-01T12:00:00Z') + fillerIndex * 60 * 60 * 1000).toISOString(),
                homeTeam,
                awayTeam
            );
            sequence += 1;
            fillerIndex += 1;
            schedule.push(filler);
            if (!futureSlot) futureSlot = filler;
        }
    }
    const sourceBindings = {
        gd_a01_artifact: { sha256: HASH, business_hash: HASH, schema_version: 'gd-a01-artifact/v1' },
        gd_a01_receipt: { sha256: HASH, business_hash: HASH, schema_version: 'gd-a01-receipt/v1' },
        gd_a02_artifact: { sha256: HASH, business_hash: HASH, schema_version: 'gd-a02-artifact/v2' },
        gd_a02_receipt: { sha256: HASH, business_hash: HASH, schema_version: 'gd-a02-receipt/v2' },
        canonical_schedule: { sha256: HASH, business_hash: HASH, schema_version: 'candidate-match-identity/v1' },
        feature_contract: { sha256: HASH, schema_version: 'model-feature-contract-registry/v1' },
        runtime_feature_adapter: {
            sha256: HASH,
            schema_version: 'V26_6_PreMatchAdapter.V26_6_FEATURES',
            ordered_features: featureContract.ordered_features,
        },
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
            team_closure: teamClosure(schedule),
        },
        featureContract,
        sourceBindings,
        codeRevision: REVISION,
    };
    return { options, schedule, targets, facts, targetId: target.id, futureSlot };
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

test('GD-A03 closes SOT from GD-A02 shotmap facts with exact five-match lineage', () => {
    const fixture = buildFixture();
    const facts = fixture.facts.map((row, index) => ({
        ...row,
        facts: {
            ...row.facts,
            shots_on_target: completeShotsOnTarget(index + 1, index + 1),
        },
    }));
    const result = buildPriorStateFeatureView({ ...fixture.options, factRows: facts });
    const target = targetRow(result, fixture.targetId);
    assert.equal(target.features.rolling_shots_on_target_home.value, 3);
    assert.equal(target.features.rolling_shots_on_target_away.value, 8);
    assert.equal(target.feature_vector_eligibility.status, 'NO');
    assert.ok(target.feature_vector_eligibility.reason_codes.includes(REASON_CODES.SEMANTICS_UNPROVEN));
    assert.deepEqual(target.features.rolling_shots_on_target_home.source_evidence_match_ids, [
        ...target.features.rolling_shots_on_target_home.source_match_ids,
    ]);
    assert.match(target.features.rolling_shots_on_target_home.provenance_inputs[0].field, /^facts\.shots_on_target\./);
    assert.equal(result.artifact.validation_counters.target_match_fact_dependency_count, 0);

    const targetFact = facts.find(row => row.canonical_match_id === fixture.targetId);
    targetFact.facts.shots_on_target.home.value = 999;
    const targetMutated = buildPriorStateFeatureView({ ...fixture.options, factRows: facts });
    assert.equal(
        targetRow(targetMutated, fixture.targetId).features.rolling_shots_on_target_home.value,
        target.features.rolling_shots_on_target_home.value
    );
});

test('GD-A03 SOT missing prior evidence fails closed without reaching older history', () => {
    const fixture = buildFixture({ includeSixth: true });
    const facts = fixture.facts.map((row, index) => ({
        ...row,
        facts: {
            ...row.facts,
            shots_on_target: completeShotsOnTarget(index + 1, index + 1),
        },
    }));
    const missingId = fixture.schedule.find(row => row.kickoff_at === '2024-07-09T12:00:00Z').id;
    const missing = facts.find(row => row.canonical_match_id === missingId);
    missing.facts.shots_on_target = {
        ...missing.facts.shots_on_target,
        status: 'UNAVAILABLE',
        unavailable_reason_code: REASON_CODES.SOT_OWN_GOAL_SEMANTICS_UNPROVEN,
        total_shots: null,
        shots_with_on_target: null,
        shots_without_on_target: null,
        home: { value: null, status: 'UNAVAILABLE', known_shots: 0, missing_shots: 0 },
        away: { value: null, status: 'UNAVAILABLE', known_shots: 0, missing_shots: 0 },
    };
    const result = buildPriorStateFeatureView({ ...fixture.options, factRows: facts });
    const line = targetRow(result, fixture.targetId).features.rolling_shots_on_target_home;
    assert.equal(line.value, null);
    assert.equal(line.source_match_ids.length, 5);
    assert.ok(line.source_match_ids.includes(missingId));
    assert.ok(line.unavailable_reason_codes.includes(REASON_CODES.HISTORY_GAP));
    assert.ok(line.unavailable_reason_codes.includes(REASON_CODES.SOT_OWN_GOAL_SEMANTICS_UNPROVEN));
    assert.equal(result.artifact.validation_counters.silent_history_gap_count, 0);
});

test('GD-A03 SOT earlier target is invariant under later source-fact mutation', () => {
    const fixture = buildFixture();
    const facts = fixture.facts.map((row, index) => ({
        ...row,
        facts: {
            ...row.facts,
            shots_on_target: completeShotsOnTarget(index + 1, index + 1),
        },
    }));
    const future = candidate(
        '47_20242025_9999999',
        '2024-07-20T12:00:00Z',
        fixture.futureSlot.home_team,
        fixture.futureSlot.away_team
    );
    const scheduleWithFuture = fixture.schedule.map(row => (row.id === fixture.futureSlot.id ? future : row));
    const futureFactBase = fact(future, 99);
    const futureFact = {
        ...futureFactBase,
        facts: {
            ...futureFactBase.facts,
            shots_on_target: completeShotsOnTarget(7, 8),
        },
    };
    const options = {
        ...fixture.options,
        scheduleCandidates: scheduleWithFuture,
        targetRows: [...fixture.options.targetRows, { ...future, canonical_match_id: future.id }],
        factRows: [...facts, futureFact],
        scheduleClosure: {
            ...fixture.options.scheduleClosure,
            per_season_expected_counts: { '2024/2025': scheduleWithFuture.length },
            team_closure: teamClosure(scheduleWithFuture),
        },
    };
    const baseline = buildPriorStateFeatureView(options);
    const mutatedFutureFact = {
        ...futureFact,
        facts: {
            ...futureFact.facts,
            shots_on_target: {
                ...futureFact.facts.shots_on_target,
                home: { ...futureFact.facts.shots_on_target.home, value: 999 },
            },
        },
    };
    const mutated = buildPriorStateFeatureView({ ...options, factRows: [...facts, mutatedFutureFact] });
    assert.equal(
        targetRow(mutated, fixture.targetId).features.rolling_shots_on_target_home.value,
        targetRow(baseline, fixture.targetId).features.rolling_shots_on_target_home.value
    );
    assert.equal(mutated.artifact.validation_counters.future_match_dependency_count, 0);
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

    const future = candidate(
        '47_20242025_9999999',
        '2024-07-20T12:00:00Z',
        fixture.futureSlot.home_team,
        fixture.futureSlot.away_team
    );
    const scheduleWithFuture = fixture.schedule.map(row => (row.id === fixture.futureSlot.id ? future : row));
    const futureOptions = {
        ...fixture.options,
        scheduleCandidates: scheduleWithFuture,
        scheduleClosure: {
            ...fixture.options.scheduleClosure,
            per_season_expected_counts: { '2024/2025': scheduleWithFuture.length },
            team_closure: teamClosure(scheduleWithFuture),
        },
    };
    const withFuture = buildPriorStateFeatureView(futureOptions);
    assert.deepEqual(targetRow(withFuture, fixture.targetId).features, targetRow(base, fixture.targetId).features);
});

test('GD-A03 schedule normalization rejects non-canonical IDs and timestamps', () => {
    const fixture = buildFixture();
    const valid = fixture.schedule[0];
    assertReject(() => normalizeSchedule([{ ...valid, source_match_id: 'not-numeric' }]), 'IDENTITY_CONFLICT');
    assertReject(() => normalizeSchedule([{ ...valid, kickoff_at: '2024-07-03' }]), 'FACT_VALUE_INVALID');
});

test('GD-A03 team schedule closure rejects an incomplete or re-assigned fixture', () => {
    const teams = Array.from({ length: 20 }, (_, index) => `Team ${index + 1}`);
    const schedule = [];
    let sequence = 1;
    for (let homeIndex = 0; homeIndex < teams.length; homeIndex += 1) {
        for (let awayIndex = homeIndex + 1; awayIndex < teams.length; awayIndex += 1) {
            for (const [home, away] of [
                [teams[homeIndex], teams[awayIndex]],
                [teams[awayIndex], teams[homeIndex]],
            ]) {
                schedule.push(
                    candidate(`47_20242025_${String(sequence).padStart(7, '0')}`, '2024-07-01T12:00:00Z', home, away)
                );
                sequence += 1;
            }
        }
    }
    const closure = {
        schema_version: 'canonical-schedule-history/v1',
        status: 'PROVEN',
        authority: 'fixture canonical schedule',
        per_season_expected_counts: { '2024/2025': 380 },
        team_closure: {
            schema_version: SCHEDULE_TEAM_CLOSURE_SCHEMA_VERSION,
            status: 'PROVEN',
            teams_per_season: 20,
            fixtures_per_team: 38,
            home_fixtures_per_team: 19,
            away_fixtures_per_team: 19,
            per_team_counts: teamClosure(schedule).per_team_counts,
        },
    };
    assert.doesNotThrow(() => validateScheduleClosure(normalizeSchedule(schedule), closure));
    const tampered = schedule.map(row => ({ ...row }));
    tampered[0].home_team = 'Reassigned Team';
    assertReject(() => validateScheduleClosure(normalizeSchedule(tampered), closure), 'HISTORY_CLOSURE_INVALID');
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

test('GD-A03 requires canonical readiness to remain fail-closed', () => {
    const result = build(buildFixture());
    const tampered = JSON.parse(result.artifactBytes.toString('utf8'));
    tampered.feature_frame_readiness = 'READY_FOR_SEPARATE_TRAINING_REVIEW';
    assertReject(() => validatePriorStateArtifact(tampered), 'READINESS_BOUNDARY');
});

test('GD-A03 requires team-level schedule closure and complete source bindings', () => {
    const fixture = buildFixture();
    assertReject(
        () =>
            buildPriorStateFeatureView({
                ...fixture.options,
                scheduleClosure: { ...fixture.options.scheduleClosure, team_closure: undefined },
            }),
        'HISTORY_CLOSURE_INVALID'
    );

    assertReject(
        () =>
            buildPriorStateFeatureView({
                ...fixture.options,
                scheduleClosure: {
                    ...fixture.options.scheduleClosure,
                    team_closure: { ...fixture.options.scheduleClosure.team_closure, fixtures_per_team: 1 },
                },
            }),
        'HISTORY_CLOSURE_INVALID'
    );

    const result = build(fixture);
    const tampered = JSON.parse(result.artifactBytes.toString('utf8'));
    delete tampered.source_bindings.gd_a02_receipt;
    assertReject(() => validatePriorStateArtifact(tampered), 'PROVENANCE_INVALID');

    const nonCanonicalClosure = JSON.parse(result.artifactBytes.toString('utf8'));
    nonCanonicalClosure.schedule_authority.team_closure.teams_per_season = 19;
    assertReject(() => validatePriorStateArtifact(nonCanonicalClosure), 'HISTORY_CLOSURE_INVALID');

    const missingPopulationHash = JSON.parse(result.artifactBytes.toString('utf8'));
    delete missingPopulationHash.population_accounting.target_id_set_sha256;
    assertReject(() => validatePriorStateArtifact(missingPopulationHash), 'HASH_MISMATCH');
});

test('GD-A03 independently validates target-label identity, projection, and digest', () => {
    const result = build(buildFixture());
    const identityTampered = JSON.parse(result.artifactBytes.toString('utf8'));
    identityTampered.rows[0].target_label.canonical_match_id = 'tampered-target';
    assertReject(() => validatePriorStateArtifact(identityTampered), 'PROVENANCE_INVALID');

    const projectionTampered = JSON.parse(result.artifactBytes.toString('utf8'));
    projectionTampered.rows[0].target_label.outcome = 'home';
    assertReject(() => validatePriorStateArtifact(projectionTampered), 'FACT_VALUE_INVALID');

    const digestTampered = JSON.parse(result.artifactBytes.toString('utf8'));
    digestTampered.rows[0].target_label.provenance_input.result.home_score += 1;
    assertReject(() => validatePriorStateArtifact(digestTampered), 'PROVENANCE_INVALID');
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
