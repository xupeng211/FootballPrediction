'use strict';

/* eslint-disable max-lines -- GD-A03 lineage and fail-closed invariants stay in one permanent contract suite. */

// lifecycle: permanent；GD-A03 runtime behavior / fail-closed / determinism tests。
// 真实 888 离线验证使用同一 assembler，由任务级 external validation 执行。

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const featureContract = require('../../config/model_feature_contracts.json').contracts[0];
const { admittedIdSetHash } = require('../../src/infrastructure/golden_dataset/GdA01AssemblyContract');
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
    computeFactRejectionBinding,
    computeFactRejectionBindingsHash,
    computeFactResultBinding,
    computeFactResultBindingsHash,
    computeProvenanceDigest,
    stableStringify,
} = require('../../src/infrastructure/golden_dataset/GdA03PriorStateContract');

const REVISION = 'b'.repeat(40);
const HASH = 'a'.repeat(64);

function digest(value) {
    return crypto.createHash('sha256').update(stableStringify(value)).digest('hex');
}

function temporaryContractRepository(document) {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'gd-a03-contract-'));
    fs.mkdirSync(path.join(root, 'config'), { recursive: true });
    fs.mkdirSync(path.join(root, 'src/ml/feature_adapters'), { recursive: true });
    fs.copyFileSync(
        path.resolve(__dirname, '../../src/ml/feature_adapters/prematch.py'),
        path.join(root, 'src/ml/feature_adapters/prematch.py')
    );
    fs.writeFileSync(path.join(root, 'config/model_feature_contracts.json'), JSON.stringify(document), 'utf8');
    return root;
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
        shots_without_on_target: 2,
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
    const factResultBindings = facts.map(row => ({
        canonical_match_id: row.canonical_match_id,
        fact_result_binding: computeFactResultBinding({
            canonicalMatchId: row.canonical_match_id,
            result: row.facts.match_result,
            sourceProvenance: row.provenance,
        }),
    }));
    const factRejectionBindings = [];
    const sourceBindings = {
        gd_a01_artifact: { sha256: HASH, business_hash: HASH, schema_version: 'gd-a01-artifact/v1' },
        gd_a01_receipt: {
            sha256: HASH,
            business_hash: HASH,
            schema_version: 'gd-a01-receipt/v1',
            admitted_id_set_sha256: admittedIdSetHash(targets.map(row => row.id)),
            admitted_row_count: targets.length,
        },
        gd_a02_artifact: {
            sha256: HASH,
            business_hash: HASH,
            schema_version: 'gd-a02-artifact/v2',
            fact_result_bindings_sha256: computeFactResultBindingsHash(factResultBindings),
            fact_result_binding_count: factResultBindings.length,
            fact_rejection_bindings_sha256: computeFactRejectionBindingsHash(factRejectionBindings),
            fact_rejection_binding_count: factRejectionBindings.length,
            fact_admitted_id_set_sha256: admittedIdSetHash(facts.map(row => row.canonical_match_id)),
            fact_admitted_row_count: facts.length,
            fact_rejected_id_set_sha256: admittedIdSetHash([]),
            fact_rejected_row_count: 0,
            fact_accounted_id_set_sha256: admittedIdSetHash(facts.map(row => row.canonical_match_id)),
            fact_accounted_row_count: facts.length,
        },
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
        factRejections: [],
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

function runtimeContextForFixture(fixture) {
    const target = fixture.schedule.find(row => row.id === fixture.targetId);
    const factsById = new Map(fixture.facts.map(row => [row.canonical_match_id, row]));
    const priorMatches = fixture.schedule
        .filter(row => row.kickoff_at < target.kickoff_at)
        .map(row => {
            const sourceFact = factsById.get(row.id);
            return {
                canonical_match_id: row.id,
                kickoff_utc: row.kickoff_at,
                competition: row.competition,
                season: row.season,
                home_team: row.home_team,
                away_team: row.away_team,
                home_xg: sourceFact?.facts?.xg?.home?.value ?? null,
                away_xg: sourceFact?.facts?.xg?.away?.value ?? null,
                outcome: sourceFact?.facts?.match_result?.outcome,
                available_at_utc: null,
            };
        });
    return {
        canonical_match_id: target.id,
        home_team: target.home_team,
        away_team: target.away_team,
        competition: target.competition,
        season: target.season,
        target_kickoff_utc: target.kickoff_at,
        feature_as_of_utc: target.kickoff_at,
        model_decision_time_utc: null,
        history_closure: {
            status: 'PROVEN',
            authority: 'canonical-schedule-history/v1',
            competition: target.competition,
            season: target.season,
            team_names: [target.home_team, target.away_team].sort(),
            prior_match_ids: priorMatches.map(row => row.canonical_match_id),
        },
        prior_matches: priorMatches,
    };
}

function canonicalRuntimeProjection(context) {
    const script = [
        'import json, sys',
        'from src.ml.feature_adapters.prematch import V26_6_PreMatchAdapter',
        'context = json.load(sys.stdin)',
        'result = V26_6_PreMatchAdapter().adapt_canonical_typed_context(context)',
        'payload = {"success": result.success, "feature_names": result.feature_names, "missing_features": result.missing_features}',
        'if result.features is not None: payload["features"] = result.features.iloc[0].to_dict()',
        'print(json.dumps(payload, sort_keys=True))',
    ].join('\n');
    const completed = spawnSync('python3', ['-c', script], {
        cwd: path.resolve(__dirname, '../..'),
        input: JSON.stringify(context),
        encoding: 'utf8',
    });
    assert.equal(completed.status, 0, completed.stderr);
    return JSON.parse(completed.stdout);
}

test('GD-A03 historical values equal the isolated canonical runtime adapter on typed context', () => {
    const fixture = buildFixture();
    const historical = build(fixture).artifact.rows.find(row => row.canonical_match_id === fixture.targetId);
    const runtime = canonicalRuntimeProjection(runtimeContextForFixture(fixture));
    const accepted = loadFeatureContract(path.resolve(__dirname, '../..')).vNextContract.feature_statuses
        .filter(status => status.training_decision === 'ACCEPTED_FOR_TRAINING')
        .map(status => status.feature_name);

    assert.equal(runtime.success, true);
    assert.deepEqual(runtime.feature_names, accepted);
    for (const featureName of accepted) {
        assert.equal(historical.features[featureName].availability_status, 'AVAILABLE');
        assert.equal(runtime.features[featureName], historical.features[featureName].value);
    }
});

function rebindSourceBindings(options) {
    const targetIds = options.targetRows.map(row => row.canonical_match_id);
    const factRejections = options.factRejections || [];
    const factResultBindings = options.factRows.map(row => ({
        canonical_match_id: row.canonical_match_id,
        fact_result_binding: computeFactResultBinding({
            canonicalMatchId: row.canonical_match_id,
            result: row.facts.match_result,
            sourceProvenance: row.provenance,
        }),
    }));
    const factRejectionBindings = factRejections.map(row => ({
        canonical_match_id: row.canonical_match_id,
        fact_rejection_binding: computeFactRejectionBinding({
            canonicalMatchId: row.canonical_match_id,
            sourceMatchId: row.source_match_id,
            rejectionReason: row.admission.rejection_reason,
            errorCode: row.error_code,
            reason: row.reason,
        }),
    }));
    return {
        ...options,
        sourceBindings: {
            ...options.sourceBindings,
            gd_a01_receipt: {
                ...options.sourceBindings.gd_a01_receipt,
                admitted_id_set_sha256: admittedIdSetHash(targetIds),
                admitted_row_count: targetIds.length,
            },
            gd_a02_artifact: {
                ...options.sourceBindings.gd_a02_artifact,
                fact_result_bindings_sha256: computeFactResultBindingsHash(factResultBindings),
                fact_result_binding_count: factResultBindings.length,
                fact_rejection_bindings_sha256: computeFactRejectionBindingsHash(factRejectionBindings),
                fact_rejection_binding_count: factRejectionBindings.length,
                fact_admitted_id_set_sha256: admittedIdSetHash(options.factRows.map(row => row.canonical_match_id)),
                fact_admitted_row_count: options.factRows.length,
                fact_rejected_id_set_sha256: admittedIdSetHash(factRejections.map(row => row.canonical_match_id)),
                fact_rejected_row_count: factRejections.length,
                fact_accounted_id_set_sha256: admittedIdSetHash([
                    ...options.factRows.map(row => row.canonical_match_id),
                    ...factRejections.map(row => row.canonical_match_id),
                ]),
                fact_accounted_row_count: options.factRows.length + factRejections.length,
            },
        },
    };
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
    const poisoned = buildPriorStateFeatureView(rebindSourceBindings({ ...fixture.options, factRows: mutatedFacts }));
    assert.deepEqual(targetRow(poisoned, fixture.targetId).features, target.features);
    assert.notDeepEqual(targetRow(poisoned, fixture.targetId).target_label, target.target_label);
});

test('GD-A03 name/order identity matches config and V26_6_PreMatchAdapter', () => {
    const loaded = loadFeatureContract(path.resolve(__dirname, '../..'));
    assert.deepEqual(loaded.contract.ordered_features, loaded.runtimeFeatureAdapter.orderedFeatures);
    assert.equal(loaded.runtimeFeatureAdapter.symbol, 'V26_6_PreMatchAdapter.V26_6_FEATURES');
    assert.equal(loaded.registrySchemaVersion, 'model-feature-contract-registry/v2');
});

test('GD-A03 rejects an incomplete v2 registry before artifact assembly', () => {
    const document = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../../config/model_feature_contracts.json')));
    delete document.migration_map;
    const repositoryRoot = temporaryContractRepository(document);
    try {
        assert.throws(
            () => loadFeatureContract(repositoryRoot),
            error => error.code === 'SCHEMA_MISMATCH' && /v2 fields|migration map/.test(error.message)
        );
    } finally {
        fs.rmSync(repositoryRoot, { recursive: true, force: true });
    }
});

test('GD-A03 rejects the legacy registry schema without an explicit compatibility path', () => {
    const document = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../../config/model_feature_contracts.json')));
    document.schema_version = 'model-feature-contract-registry/v1';
    delete document.migration_map;
    delete document.decision_boundaries;
    const repositoryRoot = temporaryContractRepository(document);
    try {
        assert.throws(
            () => loadFeatureContract(repositoryRoot),
            error => error.code === 'SCHEMA_MISMATCH' && /v2 fields|schema or lifecycle/.test(error.message)
        );
    } finally {
        fs.rmSync(repositoryRoot, { recursive: true, force: true });
    }
});

test('GD-A03 rejects a v2 registry without the non-activated V-next contract', () => {
    const document = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../../config/model_feature_contracts.json')));
    document.contracts = document.contracts.filter(contract => contract.contract_id !== 'canonical_prematch/vnext-v1');
    const repositoryRoot = temporaryContractRepository(document);
    try {
        assert.throws(
            () => loadFeatureContract(repositoryRoot),
            error => error.code === 'SCHEMA_MISMATCH' && /V1 and V-next/.test(error.message)
        );
    } finally {
        fs.rmSync(repositoryRoot, { recursive: true, force: true });
    }
});

test('GD-A03 rejects decision-boundary value drift before artifact assembly', () => {
    const document = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../../config/model_feature_contracts.json')));
    document.decision_boundaries.raw_elo.training_eligible = 'YES';
    const repositoryRoot = temporaryContractRepository(document);
    try {
        assert.throws(
            () => loadFeatureContract(repositoryRoot),
            error => error.code === 'SCHEMA_MISMATCH' && /raw ELO decision boundary/.test(error.message)
        );
    } finally {
        fs.rmSync(repositoryRoot, { recursive: true, force: true });
    }
});

test('GD-A03 rejects an unresolved standings rule-history flag after closure', () => {
    const document = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../../config/model_feature_contracts.json')));
    document.decision_boundaries.standings.rule_history_closure_required = 'YES';
    const repositoryRoot = temporaryContractRepository(document);
    try {
        assert.throws(
            () => loadFeatureContract(repositoryRoot),
            error => error.code === 'SCHEMA_MISMATCH' && /standings decision boundary/.test(error.message)
        );
    } finally {
        fs.rmSync(repositoryRoot, { recursive: true, force: true });
    }
});

test('GD-A03 rejects a non-object frozen standings contract before artifact assembly', () => {
    const document = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../../config/model_feature_contracts.json')));
    document.decision_boundaries.standings.contract = null;
    const repositoryRoot = temporaryContractRepository(document);
    try {
        assert.throws(
            () => loadFeatureContract(repositoryRoot),
            error => error.code === 'SCHEMA_MISMATCH' && /standings semantic contract/.test(error.message)
        );
    } finally {
        fs.rmSync(repositoryRoot, { recursive: true, force: true });
    }
});

test('GD-A03 rejects V-next feature-status value drift before artifact assembly', () => {
    const document = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../../config/model_feature_contracts.json')));
    document.contracts[1].feature_statuses[0].runtime_source_status = 'PROVEN';
    const repositoryRoot = temporaryContractRepository(document);
    try {
        assert.throws(
            () => loadFeatureContract(repositoryRoot),
            error => error.code === 'SCHEMA_MISMATCH' && /feature status values/.test(error.message)
        );
    } finally {
        fs.rmSync(repositoryRoot, { recursive: true, force: true });
    }
});

test('GD-A03 rejects an orphaned V-next migration target before artifact assembly', () => {
    const document = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../../config/model_feature_contracts.json')));
    document.migration_map.entries[0].to_feature = 'rolling_xg_away';
    const repositoryRoot = temporaryContractRepository(document);
    try {
        assert.throws(
            () => loadFeatureContract(repositoryRoot),
            error => error.code === 'SCHEMA_MISMATCH' && /target coverage/.test(error.message)
        );
    } finally {
        fs.rmSync(repositoryRoot, { recursive: true, force: true });
    }
});

test('GD-A03 rejects stale standings migration metadata before artifact assembly', () => {
    const document = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../../config/model_feature_contracts.json')));
    const standingsFeatures = new Set(['home_table_position', 'away_table_position', 'table_position_diff']);
    document.migration_map.entries.forEach(entry => {
        if (standingsFeatures.has(entry.from_feature)) {
            entry.classification = 'CONTRACT_PENDING';
            entry.reason = 'Official rule history and exception closure are still required.';
        }
    });
    const repositoryRoot = temporaryContractRepository(document);
    try {
        assert.throws(
            () => loadFeatureContract(repositoryRoot),
            error => error.code === 'SCHEMA_MISMATCH' && /standings migration metadata/.test(error.message)
        );
    } finally {
        fs.rmSync(repositoryRoot, { recursive: true, force: true });
    }
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
    targetFact.facts.shots_on_target = completeShotsOnTarget(0, targetFact.facts.shots_on_target.away.value);
    const targetMutated = buildPriorStateFeatureView({ ...fixture.options, factRows: facts });
    assert.equal(
        targetRow(targetMutated, fixture.targetId).features.rolling_shots_on_target_home.value,
        target.features.rolling_shots_on_target_home.value
    );
});

test('GD-A03 rejects an unvalidated SOT value before deriving prior-state features', () => {
    const fixture = buildFixture();
    const facts = fixture.facts.map((row, index) => ({
        ...row,
        facts: {
            ...row.facts,
            shots_on_target: completeShotsOnTarget(index + 1, index + 1),
        },
    }));
    const sourceFact = facts.find(row => row.canonical_match_id !== fixture.targetId);
    sourceFact.facts.shots_on_target.home = {
        ...sourceFact.facts.shots_on_target.home,
        value: 999,
    };

    assertReject(
        () => buildPriorStateFeatureView(rebindSourceBindings({ ...fixture.options, factRows: facts })),
        'FACT_VALUE_INVALID'
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
    const baseline = buildPriorStateFeatureView(rebindSourceBindings(options));
    const mutatedFutureFact = {
        ...futureFact,
        facts: {
            ...futureFact.facts,
            shots_on_target: completeShotsOnTarget(0, 8),
        },
    };
    const mutated = buildPriorStateFeatureView(
        rebindSourceBindings({ ...options, factRows: [...facts, mutatedFutureFact] })
    );
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
    const missingSource = complete.schedule.find(row => row.id === missingId);
    const missingFactOptions = {
        ...complete.options,
        factRows: complete.facts.filter(row => row.canonical_match_id !== missingId),
    };
    assertReject(() => buildPriorStateFeatureView(rebindSourceBindings(missingFactOptions)), 'POPULATION_MISMATCH');
    const options = {
        ...complete.options,
        factRows: complete.facts.filter(row => row.canonical_match_id !== missingId),
        factRejections: [
            {
                canonical_match_id: missingId,
                source_match_id: missingSource.source_match_id,
                admission: { status: 'REJECTED', rejection_reason: 'GD_A02_FACT_INPUT_REJECTED' },
                error_code: 'TEST_MISSING_FACT',
                reason: 'frozen GD-A02 fact intentionally unavailable in test fixture',
            },
        ],
    };
    const result = buildPriorStateFeatureView(rebindSourceBindings(options));
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
    assert.equal(result.artifact.rows.length, complete.options.targetRows.length);
    const missingLabel = targetRow(result, missingId).target_label;
    assert.equal(missingLabel.source_fact_binding.fact_presence, 'MISSING');
    assert.equal(missingLabel.provenance_input.result, null);
});

test('GD-A03 rejects tampered rejected-fact provenance after business hashes are rewritten', () => {
    const complete = buildFixture({ includeSixth: true });
    const missingId = complete.schedule.find(row => row.kickoff_at === '2024-07-09T12:00:00Z').id;
    const missingSource = complete.schedule.find(row => row.id === missingId);
    const options = {
        ...complete.options,
        factRows: complete.facts.filter(row => row.canonical_match_id !== missingId),
        factRejections: [
            {
                canonical_match_id: missingId,
                source_match_id: missingSource.source_match_id,
                admission: { status: 'REJECTED', rejection_reason: 'GD_A02_FACT_INPUT_REJECTED' },
                error_code: 'TEST_MISSING_FACT',
                reason: 'frozen GD-A02 fact intentionally unavailable in test fixture',
            },
        ],
    };
    const result = buildPriorStateFeatureView(rebindSourceBindings(options));
    const tampered = JSON.parse(result.artifactBytes.toString('utf8'));
    const missingLabel = tampered.rows.find(row => row.canonical_match_id === missingId).target_label;
    missingLabel.provenance_input.source_provenance.rejection_message = 'tampered rejection reason';
    missingLabel.provenance_digest = computeProvenanceDigest({
        role: missingLabel.role,
        target_match_id: missingLabel.canonical_match_id,
        result: missingLabel.provenance_input.result,
        source_provenance: missingLabel.provenance_input.source_provenance,
    });
    tampered.business_content_sha256 = computeBusinessHash({ ...tampered, business_content_sha256: null });
    assertReject(() => validatePriorStateArtifact(tampered), 'PROVENANCE_INVALID');
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
        factRows: fixture.facts.filter(row => row.canonical_match_id !== missingPrior.id),
        factRejections: [
            {
                canonical_match_id: missingPrior.id,
                source_match_id: missingPrior.source_match_id,
                admission: { status: 'REJECTED', rejection_reason: 'GD_A02_FACT_INPUT_REJECTED' },
                error_code: 'TEST_MISSING_FACT',
                reason: 'frozen GD-A02 fact intentionally unavailable in test fixture',
            },
        ],
    };
    const result = buildPriorStateFeatureView(rebindSourceBindings(options));
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
    assertReject(() => validatePriorStateArtifact(digestTampered), 'FACT_VALUE_INVALID');

    const sourceFactTampered = JSON.parse(result.artifactBytes.toString('utf8'));
    sourceFactTampered.rows[0].target_label.source_fact_binding.source_business_hash = 'b'.repeat(64);
    assertReject(() => validatePriorStateArtifact(sourceFactTampered), 'PROVENANCE_INVALID');

    const unavailableResultWithScore = JSON.parse(result.artifactBytes.toString('utf8'));
    const unavailableLabel = unavailableResultWithScore.rows[0].target_label;
    unavailableLabel.provenance_input.result = {
        status: 'UNAVAILABLE',
        home_score: 3,
        away_score: 2,
        outcome: null,
        source_path: 'normalized.home_team.score + normalized.away_team.score',
    };
    unavailableLabel.status = 'UNAVAILABLE';
    unavailableLabel.outcome = null;
    unavailableLabel.provenance_digest = computeProvenanceDigest({
        role: unavailableLabel.role,
        target_match_id: unavailableLabel.canonical_match_id,
        result: unavailableLabel.provenance_input.result,
        source_provenance: unavailableLabel.provenance_input.source_provenance,
    });
    unavailableLabel.source_fact_binding.fact_result_binding = computeFactResultBinding({
        canonicalMatchId: unavailableLabel.canonical_match_id,
        result: unavailableLabel.provenance_input.result,
        sourceProvenance: unavailableLabel.provenance_input.source_provenance,
    });
    assertReject(() => validatePriorStateArtifact(unavailableResultWithScore), 'FACT_VALUE_INVALID');

    const independentlyRewrittenLabel = JSON.parse(result.artifactBytes.toString('utf8'));
    const rewrittenLabel = independentlyRewrittenLabel.rows[0].target_label;
    rewrittenLabel.provenance_input.result = {
        ...rewrittenLabel.provenance_input.result,
        home_score: 100,
        away_score: 0,
        outcome: 'home',
    };
    rewrittenLabel.status = 'AVAILABLE';
    rewrittenLabel.outcome = 'home';
    rewrittenLabel.provenance_digest = computeProvenanceDigest({
        role: rewrittenLabel.role,
        target_match_id: rewrittenLabel.canonical_match_id,
        result: rewrittenLabel.provenance_input.result,
        source_provenance: rewrittenLabel.provenance_input.source_provenance,
    });
    rewrittenLabel.source_fact_binding.fact_result_binding = computeFactResultBinding({
        canonicalMatchId: rewrittenLabel.canonical_match_id,
        result: rewrittenLabel.provenance_input.result,
        sourceProvenance: rewrittenLabel.provenance_input.source_provenance,
    });
    assertReject(() => validatePriorStateArtifact(independentlyRewrittenLabel), 'PROVENANCE_INVALID');
});

test('GD-A03 binds the population to GD-A01 independently of artifact row accounting', () => {
    const result = build(buildFixture());
    const shrunk = JSON.parse(result.artifactBytes.toString('utf8'));
    shrunk.rows.pop();
    shrunk.population_accounting.target_population_count = shrunk.rows.length;
    shrunk.population_accounting.rows_accounted = shrunk.rows.length;
    shrunk.population_accounting.target_id_set_sha256 = admittedIdSetHash(
        shrunk.rows.map(row => row.canonical_match_id)
    );
    shrunk.population_accounting.accounted_id_set_sha256 = shrunk.population_accounting.target_id_set_sha256;
    assertReject(() => validatePriorStateArtifact(shrunk), 'POPULATION_MISMATCH');
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
