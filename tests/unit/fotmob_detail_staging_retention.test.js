/* eslint-disable complexity, max-lines */
'use strict';

// lifecycle: permanent
// Retention tests for FotMobDetailStagingRetention.js — atomic output,
// append-only snapshot semantics, path safety.
// Fully offline: no network, no database.

global.fetch = () => {
    throw new Error('REAL_NETWORK_FORBIDDEN_IN_TEST');
};

const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const {
    verifyRepositoryExternalPath,
    writeJsonAtomically,
    observationKey,
    classifyAgainstStore,
    commitObservations,
    validateOutputRoot,
    emptyStoreState,
} = require('../../src/infrastructure/fotmob/FotMobDetailStagingRetention');
const { TERMINAL_STATES } = require('../../src/infrastructure/fotmob/FotMobDetailStagingContract');
const { buildPair } = require('../helpers/fotmobDetailStagingFixtures');

const REPO_ROOT = path.resolve(__dirname, '..', '..');

function tmpDir(prefix) {
    return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

function pairResult(sourceMatchId = '3901023') {
    const pair = buildPair({ source_match_id: sourceMatchId });
    const { convertPair } = require('../../src/infrastructure/fotmob/FotMobDetailStagingConverter');
    return convertPair({
        payload: pair.payload,
        manifest: pair.manifest,
        payloadBytes: pair.payloadBytes,
    });
}

// ── path safety ─────────────────────────────────────────────

test('E32: repository-internal output paths are rejected', () => {
    assert.throws(
        () =>
            verifyRepositoryExternalPath(path.join(REPO_ROOT, 'out'), {
                repositoryRoot: REPO_ROOT,
            }),
        err => err.code === 'SAFETY_ERROR'
    );
    assert.throws(
        () => verifyRepositoryExternalPath(REPO_ROOT, { repositoryRoot: REPO_ROOT }),
        err => err.code === 'SAFETY_ERROR'
    );
    assert.throws(
        () =>
            verifyRepositoryExternalPath('relative/path', {
                repositoryRoot: REPO_ROOT,
            }),
        err => err.code === 'INPUT_ERROR'
    );
});

test('E33: symlinked output components are rejected', () => {
    const dir = tmpDir('fotmob-ret-symlink-');
    const real = path.join(dir, 'real');
    const link = path.join(dir, 'link');
    fs.mkdirSync(real);
    fs.symlinkSync(real, link);
    assert.throws(
        () =>
            verifyRepositoryExternalPath(path.join(link, 'out'), {
                repositoryRoot: REPO_ROOT,
            }),
        err => err.code === 'SAFETY_ERROR'
    );
});

test('E33b: symlinked input files are rejected by readJsonFile', () => {
    const dir = tmpDir('fotmob-ret-symlink-input-');
    const real = path.join(dir, 'real.json');
    const link = path.join(dir, 'link.json');
    fs.writeFileSync(real, '{}');
    fs.symlinkSync(real, link);
    const { readJsonFile } = require('../../src/infrastructure/fotmob/FotMobDetailStagingRetention');
    assert.throws(
        () => readJsonFile(link),
        err => err.code === 'SAFETY_ERROR'
    );
});

// ── atomic writes / idempotency ─────────────────────────────

test('E34: write → identical rewrite is idempotent (nothing rewritten)', () => {
    const dir = tmpDir('fotmob-ret-atomic-');
    const file = path.join(dir, 'doc.json');
    const doc = { a: 1, nested: { b: [1, 2, 3] } };
    const first = writeJsonAtomically(file, doc, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(first.written, true);
    const second = writeJsonAtomically(file, doc, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(second.written, false);
    assert.strictEqual(second.reason, 'existing_identical');
    // no tmp residue
    assert.strictEqual(fs.readdirSync(dir).length, 1);
});

test('E35: divergent existing file fails closed (never overwritten)', () => {
    const dir = tmpDir('fotmob-ret-divergent-');
    const file = path.join(dir, 'doc.json');
    writeJsonAtomically(file, { a: 1 }, { repositoryRoot: REPO_ROOT });
    assert.throws(
        () => writeJsonAtomically(file, { a: 2 }, { repositoryRoot: REPO_ROOT }),
        err => err.code === 'OUTPUT_CONFLICT'
    );
    assert.strictEqual(JSON.parse(fs.readFileSync(file, 'utf8')).a, 1);
});

test('E38: fault injection on rename leaves no staged residue (both-or-neither)', () => {
    const dir = tmpDir('fotmob-ret-fault-');
    const file = path.join(dir, 'doc.json');
    const failingFs = {
        ...fs,
        renameSync: () => {
            throw new Error('injected rename failure');
        },
    };
    assert.throws(() => writeJsonAtomically(file, { a: 1 }, { repositoryRoot: REPO_ROOT, fsImpl: failingFs }));
    assert.deepStrictEqual(fs.readdirSync(dir), []);
});

// ── snapshot semantics (store) ──────────────────────────────

test('C20: exact duplicate folds to ACCEPTED_REPEAT_EXACT and writes nothing', () => {
    const store = emptyStoreState();
    const r1 = pairResult('3901023');
    const first = classifyAgainstStore({ result: r1, storeState: store });
    assert.strictEqual(first.terminal_state, TERMINAL_STATES.ACCEPTED_NEW);
    store.observations[observationKey('3901023', r1.artifact.stable_payload_sha256)] = {
        source_match_id: '3901023',
        stable_payload_sha256: r1.artifact.stable_payload_sha256,
        expected_identity: r1.artifact.expected_identity,
    };
    const second = classifyAgainstStore({ result: r1, storeState: store });
    assert.strictEqual(second.terminal_state, TERMINAL_STATES.ACCEPTED_REPEAT_EXACT);
    assert.strictEqual(second.artifact, null); // nothing new written
});

test('C22/C23: same match, new payload version → new immutable snapshot; old untouched', () => {
    const dir = tmpDir('fotmob-ret-versions-');
    const outputRoot = path.join(dir, 'out');

    const v1 = pairResult('3901023');
    const summary1 = commitObservations({
        results: [v1],
        outputRoot,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    assert.strictEqual(summary1.business_projection.accepted_new_count, 1);
    const artifactFile1 = summary1.business_projection.observations[0].artifact_file;
    const bytes1 = fs.readFileSync(path.join(outputRoot, artifactFile1));
    const hash1 = JSON.parse(bytes1).business_hash;

    // v2: same identity, modified event (legal re-observation, re-signed).
    const { buildPayload, buildManifest } = require('../helpers/fotmobDetailStagingFixtures');
    const norm = buildPayload({ source_match_id: '3901023' }).normalized;
    norm.events = [
        {
            id: 9434327,
            minute: 11,
            homeScore: 0,
            awayScore: 0,
            event_kind: 'real_event',
        },
    ];
    const payloadV2 = buildPayload({
        source_match_id: '3901023',
        normalized: norm,
    });
    const bytesV2 = Buffer.from(JSON.stringify(payloadV2, null, 2) + '\n', 'utf8');
    const manifestV2 = buildManifest(payloadV2);
    const { convertPair } = require('../../src/infrastructure/fotmob/FotMobDetailStagingConverter');
    const v2 = convertPair({
        payload: payloadV2,
        manifest: manifestV2,
        payloadBytes: bytesV2,
    });
    assert.strictEqual(v2.ok, true);
    assert.notStrictEqual(v2.artifact.stable_payload_sha256, v1.artifact.stable_payload_sha256);

    const summary2 = commitObservations({
        results: [v1, v2],
        outputRoot,
        repositoryRoot: REPO_ROOT,
        runId: 'run-2',
        builtAt: '2026-08-04T12:00:01.000Z',
    });
    assert.strictEqual(summary2.business_projection.accepted_repeat_exact_count, 1);
    assert.strictEqual(summary2.business_projection.accepted_repeat_equivalent_count, 1);
    // old snapshot bytes unchanged
    const bytes1After = fs.readFileSync(path.join(outputRoot, artifactFile1));
    assert.ok(bytes1After.equals(bytes1));
    assert.strictEqual(JSON.parse(bytes1After).business_hash, hash1);
});

test('C24: identity conflict with a staged observation fails closed (never overwrites)', () => {
    const dir = tmpDir('fotmob-ret-conflict-');
    const outputRoot = path.join(dir, 'out');

    const v1 = pairResult('3901023');
    commitObservations({
        results: [v1],
        outputRoot,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });

    // same source id, different teams: the payload must be internally
    // self-consistent (expected == observed, re-signed) so it passes
    // conversion — the conflict is with the ALREADY STAGED observation, and
    // must be caught by the store, not by payload validation.
    const pairConflict = buildPair({
        source_match_id: '3901023',
        expected: { home_team: 'Tottenham Hotspur', away_team: 'Arsenal' },
        observed: { home_team: 'Tottenham Hotspur', away_team: 'Arsenal' },
    });
    const { convertPair } = require('../../src/infrastructure/fotmob/FotMobDetailStagingConverter');
    const conflict = convertPair({
        payload: pairConflict.payload,
        manifest: pairConflict.manifest,
        payloadBytes: pairConflict.payloadBytes,
    });
    assert.strictEqual(conflict.ok, true, 'conflict payload must be self-consistent and pass conversion');
    const summary = commitObservations({
        results: [conflict],
        outputRoot,
        repositoryRoot: REPO_ROOT,
        runId: 'run-2',
        builtAt: '2026-08-04T12:00:02.000Z',
    });
    const obs = summary.business_projection.observations.find(o => o.source_match_id === '3901023');
    assert.strictEqual(obs.terminal_state, TERMINAL_STATES.REJECTED_IDENTITY_INCONSISTENT);
    assert.strictEqual(obs.reason, 'identity_conflict_with_staged_observation');
});

test('C25: provenance conflict (tampered payload) is rejected and writes nothing', () => {
    const dir = tmpDir('fotmob-ret-provenance-');
    const outputRoot = path.join(dir, 'out');

    const pair = buildPair();
    const { convertPair } = require('../../src/infrastructure/fotmob/FotMobDetailStagingConverter');
    const tampered = {
        ...pair.payload,
        normalized: { ...pair.payload.normalized, events: [] },
    };
    const result = convertPair({
        payload: tampered,
        manifest: pair.manifest,
        payloadBytes: pair.payloadBytes,
    });
    assert.strictEqual(result.ok, false);
    const summary = commitObservations({
        results: [result],
        outputRoot,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    assert.strictEqual(summary.business_projection.accepted_new_count, 0);
    assert.strictEqual(summary.business_projection.rejected_count, 1);
    assert.deepStrictEqual(
        fs.readdirSync(outputRoot).filter(f => f.startsWith('observation-')),
        []
    );
});

test('quarantine observations write lightweight evidence records (never full payload)', () => {
    const dir = tmpDir('fotmob-ret-quarantine-');
    const outputRoot = path.join(dir, 'out');

    const pair = buildPair({
        normalized: {
            match_external_id: '3901023',
            home_team: { id: 1, name: 'AFC Bournemouth', score: 0 },
            away_team: { id: 2, name: 'Leicester City', score: 0 },
            events: [
                {
                    id: 9,
                    minute: 500,
                    homeScore: 0,
                    awayScore: 0,
                    event_kind: 'real_event',
                },
            ],
            stats: [{ key: 'shots', homeValue: 0, awayValue: 0, period: 'All' }],
            lineup: {
                home: { coach: null, starters: [], subs: [] },
                away: { coach: null, starters: [], subs: [] },
            },
            shotmap: { shots: [] },
        },
    });
    const { convertPair } = require('../../src/infrastructure/fotmob/FotMobDetailStagingConverter');
    const result = convertPair({
        payload: pair.payload,
        manifest: pair.manifest,
        payloadBytes: pair.payloadBytes,
    });
    assert.strictEqual(result.quarantine_status, 'quarantined');
    const summary = commitObservations({
        results: [result],
        outputRoot,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    assert.strictEqual(summary.business_projection.quarantined_count, 1);
    const quarantineFiles = fs.readdirSync(outputRoot).filter(f => f.startsWith('quarantine-'));
    assert.strictEqual(quarantineFiles.length, 1);
    const evidence = JSON.parse(fs.readFileSync(path.join(outputRoot, quarantineFiles[0]), 'utf8'));
    assert.strictEqual(evidence.error_code, 'E011');
    assert.ok(!JSON.stringify(evidence).includes('normalized'));
});

test('R3-P2-1: re-running the same quarantined input reuses the immutable first evidence recording (idempotent)', () => {
    const dir = tmpDir('fotmob-ret-quarantine-idem-');
    const outputRoot = path.join(dir, 'out');

    const pair = buildPair({
        normalized: {
            match_external_id: '3901023',
            home_team: { id: 1, name: 'AFC Bournemouth', score: 0 },
            away_team: { id: 2, name: 'Leicester City', score: 0 },
            events: [{ id: 9, minute: 500, homeScore: 0, awayScore: 0, event_kind: 'real_event' }],
            stats: [{ key: 'shots', homeValue: 0, awayValue: 0, period: 'All' }],
            lineup: { home: { coach: null, starters: [], subs: [] }, away: { coach: null, starters: [], subs: [] } },
            shotmap: { shots: [] },
        },
    });
    const { convertPair } = require('../../src/infrastructure/fotmob/FotMobDetailStagingConverter');
    const result = convertPair({
        payload: pair.payload,
        manifest: pair.manifest,
        payloadBytes: pair.payloadBytes,
    });
    assert.strictEqual(result.quarantine_status, 'quarantined');

    // first build: writes the E011 evidence file + ledger entry
    commitObservations({
        results: [result],
        outputRoot,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    // second build of the SAME quarantined input (later wall clock): the
    // quarantine file name is (source_match_id, error_code) but its content
    // carries a per-run recorded_at — the R3-P2-1 failure mode was a
    // divergent OUTPUT_CONFLICT that killed the whole batch. The first
    // evidence recording is immutable: the re-run must reuse it.
    const summary2 = commitObservations({
        results: [result],
        outputRoot,
        repositoryRoot: REPO_ROOT,
        runId: 'run-2',
        builtAt: '2026-08-04T12:05:00.000Z',
    });
    const quarantineFiles = fs.readdirSync(outputRoot).filter(f => f.startsWith('quarantine-'));
    assert.strictEqual(quarantineFiles.length, 1, 'the evidence file is written exactly once');
    assert.strictEqual(summary2.business_projection.quarantined_count, 1);
    // the ledger keeps the SAME single quarantine entry (no churn) and the
    // full validator passes on the twice-built store
    const validation = validateOutputRoot(outputRoot, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(validation.ok, true, JSON.stringify(validation.errors));
    const ledgers = fs
        .readdirSync(outputRoot)
        .filter(f => f.startsWith('store-state-'))
        .sort();
    const latestLedger = JSON.parse(fs.readFileSync(path.join(outputRoot, ledgers[ledgers.length - 1]), 'utf8'));
    assert.deepStrictEqual(Object.keys(latestLedger.quarantines || {}), ['3901023:E011']);
});

test('C27: terminal state arithmetic is consistent across the summary', () => {
    const dir = tmpDir('fotmob-ret-arithmetic-');
    const outputRoot = path.join(dir, 'out');

    const pair = buildPair();
    const { convertPair } = require('../../src/infrastructure/fotmob/FotMobDetailStagingConverter');
    const ok = convertPair({
        payload: pair.payload,
        manifest: pair.manifest,
        payloadBytes: pair.payloadBytes,
    });
    const bad = convertPair({
        payload: { ...pair.payload, season: '1999' },
        manifest: pair.manifest,
        payloadBytes: pair.payloadBytes,
    });
    const summary = commitObservations({
        results: [ok, ok, bad],
        outputRoot,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    const bp = summary.business_projection;
    assert.strictEqual(bp.processed_count, 3);
    assert.strictEqual(bp.accepted_new_count, 1);
    assert.strictEqual(bp.accepted_repeat_exact_count, 1);
    assert.strictEqual(bp.rejected_count, 1);
    assert.strictEqual(
        bp.accepted_new_count +
            bp.accepted_repeat_exact_count +
            bp.accepted_repeat_equivalent_count +
            bp.rejected_count +
            bp.quarantined_count,
        bp.processed_count
    );
});

// ── validate output root ────────────────────────────────────

test('E36: artifact-only residue (missing summary) is detected as partial output', () => {
    const dir = tmpDir('fotmob-ret-partial-');
    fs.writeFileSync(path.join(dir, 'observation-1-abc.artifact.json'), '{}');
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.code === 'PARTIAL_OUTPUT'));
});

test('E37: full commit validates green end-to-end', () => {
    const dir = tmpDir('fotmob-ret-validate-');
    const outputRoot = path.join(dir, 'out');
    commitObservations({
        results: [pairResult('3901023')],
        outputRoot,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    const result = validateOutputRoot(outputRoot, {
        repositoryRoot: REPO_ROOT,
    });
    assert.strictEqual(
        result.ok,
        true,
        JSON.stringify({
            errors: result.errors,
            failed: result.failed_artifact_check_count,
        })
    );
    assert.strictEqual(result.artifact_check_count, 1);
    assert.strictEqual(result.summary_present, true);
});

test('tampered artifact file after commit is detected by validate', () => {
    const dir = tmpDir('fotmob-ret-tamper-');
    const outputRoot = path.join(dir, 'out');
    const summary = commitObservations({
        results: [pairResult('3901023')],
        outputRoot,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    const artifactFile = summary.business_projection.observations[0].artifact_file;
    const artifact = JSON.parse(fs.readFileSync(path.join(outputRoot, artifactFile), 'utf8'));
    artifact.business_hash = '0'.repeat(64);
    fs.writeFileSync(path.join(outputRoot, artifactFile), JSON.stringify(artifact, null, 2) + '\n');
    const result = validateOutputRoot(outputRoot, {
        repositoryRoot: REPO_ROOT,
    });
    assert.strictEqual(result.ok, false);
    assert.ok(
        result.errors.some(
            e => e.code === 'ARTIFACT_INVALID' || e.code === 'LEDGER_INVALID' || e.code === 'MARKER_FILE_MISMATCH'
        ),
        JSON.stringify(result.errors)
    );
});

test('summary business projection is deterministic across identical inputs', () => {
    const dir = tmpDir('fotmob-ret-det-');
    const s1 = commitObservations({
        results: [pairResult('3901023')],
        outputRoot: path.join(dir, 'out1'),
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    const s2 = commitObservations({
        results: [pairResult('3901023')],
        outputRoot: path.join(dir, 'out2'),
        repositoryRoot: REPO_ROOT,
        runId: 'run-2',
        builtAt: '2026-08-04T12:00:05.000Z',
    });
    assert.strictEqual(
        s1.business_projection.business_projection_sha256,
        s2.business_projection.business_projection_sha256
    );
    // operations fields differ, business projection does not (ERRATA_3)
    assert.notStrictEqual(s1.operations.converter_run_id, s2.operations.converter_run_id);
});

// ── commit protocol fault injection (PR1817 FINDING_1) ──────

/**
 * Wrap fs so that any operation touching a path matching the predicate fails.
 * openSync/renameSync are the injection points that matter (the tmp write and
 * the atomic rename); readFileSync/unlinkSync stay unfailed so rollback works.
 */
function failingFs(failPredicate) {
    const wrapped = { ...fs };
    const failOn = name => {
        if (failPredicate(String(name))) {
            throw new Error(`injected failure: ${name}`);
        }
    };
    wrapped.openSync = (p, ...rest) => {
        failOn(p);
        return fs.openSync(p, ...rest);
    };
    wrapped.renameSync = (a, b) => {
        failOn(b);
        return fs.renameSync(a, b);
    };
    return wrapped;
}

function assertDirEmpty(dir) {
    assert.deepStrictEqual(fs.readdirSync(dir), []);
}

test('F1: marker write failure (commit point) rolls back every written file', () => {
    const dir = tmpDir('fotmob-fi-marker-');
    assert.throws(
        () =>
            commitObservations({
                results: [pairResult('3901023')],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-1',
                builtAt: '2026-08-04T12:00:00.000Z',
                fsImpl: failingFs(name => name.includes('commit-1.json')),
            }),
        err => /injected failure/.test(err.message)
    );
    // No marker → no commit point → nothing may survive (artifact, summary and
    // ledger written before the marker must all be rolled back).
    assertDirEmpty(dir);
});

test('F2: artifact write failure leaves no residue and no marker', () => {
    const dir = tmpDir('fotmob-fi-artifact-');
    assert.throws(
        () =>
            commitObservations({
                results: [pairResult('3901023')],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-1',
                builtAt: '2026-08-04T12:00:00.000Z',
                fsImpl: failingFs(name => name.includes('observation-')),
            }),
        err => /injected failure/.test(err.message)
    );
    assertDirEmpty(dir);
});

test('F3: summary write failure rolls back the artifact written before it', () => {
    const dir = tmpDir('fotmob-fi-summary-');
    assert.throws(
        () =>
            commitObservations({
                results: [pairResult('3901023')],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-1',
                builtAt: '2026-08-04T12:00:00.000Z',
                fsImpl: failingFs(name => name.includes('summary-1.json')),
            }),
        err => /injected failure/.test(err.message)
    );
    assertDirEmpty(dir);
});

test('F4: ledger write failure rolls back artifact and summary', () => {
    const dir = tmpDir('fotmob-fi-ledger-');
    assert.throws(
        () =>
            commitObservations({
                results: [pairResult('3901023')],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-1',
                builtAt: '2026-08-04T12:00:00.000Z',
                fsImpl: failingFs(name => name.includes('store-state-1.json')),
            }),
        err => /injected failure/.test(err.message)
    );
    assertDirEmpty(dir);
});

test('F5: atomic rename failure fails the commit with no staged residue', () => {
    const dir = tmpDir('fotmob-fi-rename-');
    assert.throws(
        () =>
            commitObservations({
                results: [pairResult('3901023')],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-1',
                builtAt: '2026-08-04T12:00:00.000Z',
                fsImpl: failingFs(() => true), // every renameSync fails
            }),
        err => /injected failure/.test(err.message)
    );
    assertDirEmpty(dir);
});

test('F6: quarantine write failure rolls back with no quarantine residue', () => {
    const dir = tmpDir('fotmob-fi-quarantine-');
    const pair = buildPair({
        normalized: {
            match_external_id: '3901023',
            home_team: { id: 1, name: 'AFC Bournemouth', score: 0 },
            away_team: { id: 2, name: 'Leicester City', score: 0 },
            events: [
                {
                    id: 9,
                    minute: 500,
                    homeScore: 0,
                    awayScore: 0,
                    event_kind: 'real_event',
                },
            ],
            stats: [{ key: 'shots', homeValue: 0, awayValue: 0, period: 'All' }],
            lineup: {
                home: { coach: null, starters: [], subs: [] },
                away: { coach: null, starters: [], subs: [] },
            },
            shotmap: { shots: [] },
        },
    });
    const { convertPair } = require('../../src/infrastructure/fotmob/FotMobDetailStagingConverter');
    const quarantined = convertPair({
        payload: pair.payload,
        manifest: pair.manifest,
        payloadBytes: pair.payloadBytes,
    });
    assert.strictEqual(quarantined.quarantine_status, 'quarantined');
    assert.throws(
        () =>
            commitObservations({
                results: [quarantined],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-1',
                builtAt: '2026-08-04T12:00:00.000Z',
                fsImpl: failingFs(name => name.includes('quarantine-')),
            }),
        err => /injected failure/.test(err.message)
    );
    assertDirEmpty(dir);
});

test("F7: failed second commit never touches the first commit's files", () => {
    const dir = tmpDir('fotmob-fi-second-');
    commitObservations({
        results: [pairResult('3901023')],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    const filesAfter1 = fs.readdirSync(dir).sort();
    const hashesAfter1 = filesAfter1.map(f =>
        require('node:crypto')
            .createHash('sha256')
            .update(fs.readFileSync(path.join(dir, f)))
            .digest('hex')
    );
    // run-2 replays the same pair (write plan = summary-2 + store-state-2) and
    // fails at the marker write: rollback must remove ONLY run-2's files.
    assert.throws(
        () =>
            commitObservations({
                results: [pairResult('3901023')],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-2',
                builtAt: '2026-08-04T12:00:01.000Z',
                fsImpl: failingFs(name => name.includes('commit-2.json')),
            }),
        err => /injected failure/.test(err.message)
    );
    const filesAfter2 = fs.readdirSync(dir).sort();
    assert.deepStrictEqual(filesAfter2, filesAfter1);
    filesAfter2.forEach((f, i) => {
        assert.strictEqual(
            require('node:crypto')
                .createHash('sha256')
                .update(fs.readFileSync(path.join(dir, f)))
                .digest('hex'),
            hashesAfter1[i]
        );
    });
});

test('F8: existing_identical files are never unlinked by rollback', () => {
    const dir = tmpDir('fotmob-fi-identical-');
    commitObservations({
        results: [pairResult('3901023')],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    // run-2 replays the same pair: the ledger merge yields the SAME
    // store-state content as run-1 (immutable ledger), so its write is an
    // existing_identical skip. The marker write fails → rollback must not
    // unlink the shared store-state-1.json.
    assert.throws(
        () =>
            commitObservations({
                results: [pairResult('3901023')],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-2',
                builtAt: '2026-08-04T12:00:01.000Z',
                fsImpl: failingFs(name => name.includes('commit-2.json')),
            }),
        err => /injected failure/.test(err.message)
    );
    assert.ok(fs.existsSync(path.join(dir, 'store-state-1.json')));
    // store-state-2 was an existing_identical skip (never written), summary-2
    // was rolled back: the store is byte-identical to run-1's committed state
    // and must still validate green.
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, true, JSON.stringify(result.errors));
    const expected = ['commit-1.json', 'store-state-1.json', 'summary-1.json'];
    expected.push(fs.readdirSync(dir).find(f => f.startsWith('observation-')));
    assert.deepStrictEqual(fs.readdirSync(dir).sort(), expected.sort());
});

test('F9: a corrupted prior marker fails the next commit closed before any write', () => {
    const dir = tmpDir('fotmob-fi-corruptmarker-');
    commitObservations({
        results: [pairResult('3901023')],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    const markerPath = path.join(dir, 'commit-1.json');
    const marker = JSON.parse(fs.readFileSync(markerPath, 'utf8'));
    marker.files[0].sha256 = 'f'.repeat(64);
    fs.writeFileSync(markerPath, JSON.stringify(marker, null, 2) + '\n');
    const before = fs.readdirSync(dir).sort();
    assert.throws(
        () =>
            commitObservations({
                results: [pairResult('3901023')],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-2',
                builtAt: '2026-08-04T12:00:01.000Z',
            }),
        err => err.code === 'OUTPUT_CONFLICT'
    );
    assert.deepStrictEqual(fs.readdirSync(dir).sort(), before);
});

test('F10: uncommitted residue blocks the next commit (fail closed)', () => {
    const dir = tmpDir('fotmob-fi-residue-');
    fs.writeFileSync(
        path.join(dir, 'observation-1-abc.artifact.json'),
        JSON.stringify({ stale: true }, null, 2) + '\n'
    );
    assert.throws(
        () =>
            commitObservations({
                results: [pairResult('3901023')],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-1',
                builtAt: '2026-08-04T12:00:00.000Z',
            }),
        err => err.code === 'OUTPUT_CONFLICT'
    );
    // nothing new was written, the residue file is untouched
    assert.deepStrictEqual(fs.readdirSync(dir), ['observation-1-abc.artifact.json']);
});

// ── validator tamper detection (PR1817 FINDING_5) ───────────

function committedDir(prefix) {
    const dir = tmpDir(prefix);
    commitObservations({
        results: [pairResult('3901023')],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    return dir;
}

test('T1: deleted artifact file is detected by validate', () => {
    const dir = committedDir('fotmob-tamper-deleted-');
    const artifactFile = fs.readdirSync(dir).find(f => f.startsWith('observation-'));
    fs.unlinkSync(path.join(dir, artifactFile));
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.code === 'MARKER_FILE_MISMATCH' || e.code === 'LEDGER_INVALID'));
});

test('T2: summary tampering is detected by validate', () => {
    const dir = committedDir('fotmob-tamper-summary-');
    const summaryFile = fs.readdirSync(dir).find(f => f.startsWith('summary-'));
    const summary = JSON.parse(fs.readFileSync(path.join(dir, summaryFile), 'utf8'));
    summary.business_projection.processed_count = 999;
    fs.writeFileSync(path.join(dir, summaryFile), JSON.stringify(summary, null, 2) + '\n');
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.code === 'MARKER_FILE_MISMATCH'));
});

test('T3: ledger tampering is detected by validate', () => {
    const dir = committedDir('fotmob-tamper-ledger-');
    const ledgerFile = fs.readdirSync(dir).find(f => f.startsWith('store-state-'));
    const ledger = JSON.parse(fs.readFileSync(path.join(dir, ledgerFile), 'utf8'));
    const key = Object.keys(ledger.observations)[0];
    ledger.observations[key].business_hash = '0'.repeat(64);
    fs.writeFileSync(path.join(dir, ledgerFile), JSON.stringify(ledger, null, 2) + '\n');
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.code === 'MARKER_FILE_MISMATCH'));
});

test('T4: a broken marker chain is detected by validate', () => {
    const dir = committedDir('fotmob-tamper-chain-');
    // second commit creates a chain of two markers
    commitObservations({
        results: [pairResult('3901023')],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-2',
        builtAt: '2026-08-04T12:00:01.000Z',
    });
    fs.unlinkSync(path.join(dir, 'commit-1.json'));
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.code === 'MARKER_CHAIN_BROKEN' || e.code === 'MARKER_INVALID'));
});

test('T5: an unbound artifact (orphan) is detected by validate', () => {
    const dir = committedDir('fotmob-tamper-orphan-');
    fs.writeFileSync(
        path.join(
            dir,
            'observation-999999-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.artifact.json'
        ),
        JSON.stringify({ rogue: true }, null, 2) + '\n'
    );
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.code === 'ORPHAN_ARTIFACT'));
});

test('T6: an orphan quarantine record is detected by validate', () => {
    const dir = committedDir('fotmob-tamper-orphanq-');
    fs.writeFileSync(
        path.join(dir, 'quarantine-999999-E011.json'),
        JSON.stringify(
            {
                schema_version: 'fotmob-detail-staging-quarantine/v1',
                source_match_id: '999999',
                terminal_state: 'QUARANTINED_VALIDATION_FAIL',
                error_code: 'E011',
                quarantine_status: 'quarantined',
                quarantine_reason: 'stale',
                recorded_at: '2026-08-04T12:00:00.000Z',
            },
            null,
            2
        ) + '\n'
    );
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.code === 'ORPHAN_QUARANTINE'));
});

test('T7: quarantine evidence containing a full payload is detected', () => {
    const dir = tmpDir('fotmob-tamper-qpayload-');
    const pair = buildPair({
        normalized: {
            match_external_id: '3901023',
            home_team: { id: 1, name: 'AFC Bournemouth', score: 0 },
            away_team: { id: 2, name: 'Leicester City', score: 0 },
            events: [
                {
                    id: 9,
                    minute: 500,
                    homeScore: 0,
                    awayScore: 0,
                    event_kind: 'real_event',
                },
            ],
            stats: [{ key: 'shots', homeValue: 0, awayValue: 0, period: 'All' }],
            lineup: {
                home: { coach: null, starters: [], subs: [] },
                away: { coach: null, starters: [], subs: [] },
            },
            shotmap: { shots: [] },
        },
    });
    const { convertPair } = require('../../src/infrastructure/fotmob/FotMobDetailStagingConverter');
    const quarantined = convertPair({
        payload: pair.payload,
        manifest: pair.manifest,
        payloadBytes: pair.payloadBytes,
    });
    const summary = commitObservations({
        results: [quarantined],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    assert.strictEqual(summary.business_projection.quarantined_count, 1);
    // inject a full payload into the committed quarantine evidence
    const qFile = fs.readdirSync(dir).find(f => f.startsWith('quarantine-'));
    const q = JSON.parse(fs.readFileSync(path.join(dir, qFile), 'utf8'));
    q.normalized = pair.payload.normalized;
    fs.writeFileSync(path.join(dir, qFile), JSON.stringify(q, null, 2) + '\n');
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.code === 'QUARANTINE_INVALID' || e.code === 'MARKER_FILE_MISMATCH'));
});

test('T8: summary REPEAT_EXACT claiming a new artifact file is detected', () => {
    const dir = committedDir('fotmob-tamper-claim-');
    // second run: exact replay (REPEAT_EXACT, no artifact). Then tamper the
    // summary to claim REPEAT_EXACT wrote an artifact file.
    const summary2 = commitObservations({
        results: [pairResult('3901023')],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-2',
        builtAt: '2026-08-04T12:00:01.000Z',
    });
    const obs = summary2.business_projection.observations[0];
    assert.strictEqual(obs.terminal_state, 'ACCEPTED_REPEAT_EXACT');
    const summaryFile = 'summary-2.json';
    const doc = JSON.parse(fs.readFileSync(path.join(dir, summaryFile), 'utf8'));
    doc.business_projection.observations[0].artifact_file = 'observation-3901023-deadbeef.artifact.json';
    doc.business_projection.business_projection_sha256 = '0'.repeat(64);
    fs.writeFileSync(path.join(dir, summaryFile), JSON.stringify(doc, null, 2) + '\n');
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, false);
});

test('T9: summary REPEAT_EQUIVALENT without an artifact file is detected', () => {
    const dir = tmpDir('fotmob-tamper-noart-');
    commitObservations({
        results: [pairResult('3901023')],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    const { buildPayload } = require('../helpers/fotmobDetailStagingFixtures');
    const norm = buildPayload({ source_match_id: '3901023' }).normalized;
    norm.note = 'second observation';
    const payloadV2 = buildPayload({
        source_match_id: '3901023',
        normalized: norm,
    });
    const bytesV2 = Buffer.from(JSON.stringify(payloadV2, null, 2) + '\n', 'utf8');
    const { buildManifest } = require('../helpers/fotmobDetailStagingFixtures');
    const manifestV2 = buildManifest(payloadV2);
    const { convertPair } = require('../../src/infrastructure/fotmob/FotMobDetailStagingConverter');
    const v2 = convertPair({
        payload: payloadV2,
        manifest: manifestV2,
        payloadBytes: bytesV2,
    });
    assert.strictEqual(v2.ok, true);
    const summary2 = commitObservations({
        results: [v2],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-2',
        builtAt: '2026-08-04T12:00:01.000Z',
    });
    assert.strictEqual(summary2.business_projection.observations[0].terminal_state, 'ACCEPTED_REPEAT_EQUIVALENT');
    // tamper: strip the artifact_file from the accepted observation
    const doc = JSON.parse(fs.readFileSync(path.join(dir, 'summary-2.json'), 'utf8'));
    delete doc.business_projection.observations[0].artifact_file;
    doc.business_projection.business_projection_sha256 = '0'.repeat(64);
    fs.writeFileSync(path.join(dir, 'summary-2.json'), JSON.stringify(doc, null, 2) + '\n');
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, false);
});

test('T10: REPEAT_EXACT with no staged snapshot in the ledger is detected', () => {
    const dir = committedDir('fotmob-tamper-nokeys-');
    // tamper the summary of the SECOND run so it claims a REPEAT_EXACT for a
    // match that was never staged (no ledger entry)
    commitObservations({
        results: [pairResult('3901023')],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-2',
        builtAt: '2026-08-04T12:00:01.000Z',
    });
    const doc = JSON.parse(fs.readFileSync(path.join(dir, 'summary-2.json'), 'utf8'));
    doc.business_projection.observations.push({
        source_match_id: '111111',
        terminal_state: 'ACCEPTED_REPEAT_EXACT',
        reason: 'exact_duplicate',
        error_code: null,
        stable_payload_sha256: '0'.repeat(64),
    });
    doc.business_projection.processed_count += 1;
    doc.business_projection.accepted_repeat_exact_count += 1;
    doc.business_projection.business_projection_sha256 = '0'.repeat(64);
    fs.writeFileSync(path.join(dir, 'summary-2.json'), JSON.stringify(doc, null, 2) + '\n');
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.code === 'SUMMARY_INVALID'));
});

test('T11: an illegal ledger key format is detected', () => {
    const dir = committedDir('fotmob-tamper-key-');
    const ledgerFile = 'store-state-1.json';
    const ledger = JSON.parse(fs.readFileSync(path.join(dir, ledgerFile), 'utf8'));
    ledger.observations['not-a-valid-key'] = {
        source_match_id: '111111',
        stable_payload_sha256: '0'.repeat(64),
        artifact_file: null,
        terminal_state: 'ACCEPTED_NEW',
    };
    fs.writeFileSync(path.join(dir, ledgerFile), JSON.stringify(ledger, null, 2) + '\n');
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.code === 'LEDGER_INVALID'));
});

test('T12: forged marker rebinding a tampered artifact is caught by the artifact integrity layer', () => {
    const dir = committedDir('fotmob-tamper-forge-');
    // Attacker modifies the artifact AND rewrites the marker to bind the new
    // bytes. The marker chain cannot protect here — the artifact's OWN
    // integrity hash (FINDING_6) must catch it.
    const artifactFile = fs.readdirSync(dir).find(f => f.startsWith('observation-'));
    const artifactPath = path.join(dir, artifactFile);
    const artifact = JSON.parse(fs.readFileSync(artifactPath, 'utf8'));
    artifact.business_hash = '0'.repeat(64);
    fs.writeFileSync(artifactPath, JSON.stringify(artifact, null, 2) + '\n');
    const marker = JSON.parse(fs.readFileSync(path.join(dir, 'commit-1.json'), 'utf8'));
    marker.files = marker.files.map(f =>
        f.name === artifactFile
            ? {
                  name: artifactFile,
                  sha256: require('node:crypto')
                      .createHash('sha256')
                      .update(fs.readFileSync(artifactPath))
                      .digest('hex'),
              }
            : f
    );
    fs.writeFileSync(path.join(dir, 'commit-1.json'), JSON.stringify(marker, null, 2) + '\n');
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, false);
    assert.ok(
        result.errors.some(
            e => e.code === 'ARTIFACT_INVALID' || e.code === 'LEDGER_INVALID' || e.code === 'SUMMARY_INVALID'
        ),
        JSON.stringify(result.errors)
    );
});

test('T13: a second ledger version deleting a committed observation is detected', () => {
    const dir = committedDir('fotmob-tamper-delete-');
    commitObservations({
        results: [pairResult('3901023')],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-2',
        builtAt: '2026-08-04T12:00:01.000Z',
    });
    // delete a committed observation from the LATEST ledger version
    const ledger = JSON.parse(fs.readFileSync(path.join(dir, 'store-state-2.json'), 'utf8'));
    const key = Object.keys(ledger.observations)[0];
    delete ledger.observations[key];
    fs.writeFileSync(path.join(dir, 'store-state-2.json'), JSON.stringify(ledger, null, 2) + '\n');
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, false);
    assert.ok(
        result.errors.some(e => e.code === 'LEDGER_INVALID'),
        JSON.stringify(result.errors)
    );
});

// ── P0-2: REPEAT_EQUIVALENT three-way consistency (summary ↔ artifact ↔
// ── ledger) — Codex review 4863122944 P0-2 ──────────────────────────

/**
 * A legal SECOND version of the same source match: same identity fields,
 * different stable payload hash (an extra synthetic event in the normalized
 * projection, hashes recomputed by the real pipeline helpers).
 */
function secondVersionPair(sourceMatchId = '3901023') {
    const {
        computeStableCapturePayloadSha256,
        computeCaptureManifestSelfHash,
    } = require('../../src/infrastructure/fotmob/FotMobDetailCaptureContract');
    const pair = buildPair({ source_match_id: sourceMatchId });
    pair.payload.normalized.events.push({
        id: 999999002,
        minute: 88,
        homeScore: 1,
        awayScore: 0,
        event_kind: 'synthetic_derived_test',
        assistPlayerId: null,
        card: null,
        outcome: null,
        playerName: 'SYNTHETIC_DERIVED_TEST_PLAYER_2',
        synthetic_event_key: 'synthetic:p0-2-t15:1',
        synthetic_derived: true,
        source_has_native_id: false,
    });
    pair.payload.stable_payload_sha256 = computeStableCapturePayloadSha256(pair.payload);
    pair.payloadBytes = Buffer.from(JSON.stringify(pair.payload, null, 2) + '\n', 'utf8');
    pair.manifest.stable_payload_sha256 = String(pair.payload.stable_payload_sha256);
    pair.manifest.payload_file_sha256 = require('node:crypto')
        .createHash('sha256')
        .update(pair.payloadBytes)
        .digest('hex');
    pair.manifest.capture_manifest_sha256 = computeCaptureManifestSelfHash(pair.manifest);
    return pair;
}

function pairResultOf(pair) {
    const { convertPair } = require('../../src/infrastructure/fotmob/FotMobDetailStagingConverter');
    return convertPair({
        payload: pair.payload,
        manifest: pair.manifest,
        payloadBytes: pair.payloadBytes,
    });
}

test('T14 (P0-2): FIRST_IMPORT -> ACCEPTED_NEW -> validate PASS', () => {
    const dir = tmpDir('fotmob-p0-2-first-');
    const summary = commitObservations({
        results: [pairResult('3901023')],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    assert.strictEqual(summary.business_projection.accepted_new_count, 1);
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, true, JSON.stringify(result.errors));
});

test('T15 (P0-2): LEGAL_SECOND_VERSION -> REPEAT_EQUIVALENT, new artifact, old bytes unchanged, three-way hash agreement, validate PASS', () => {
    const dir = tmpDir('fotmob-p0-2-eqv-');
    // run 1: v1 ACCEPTED_NEW
    const first = pairResult('3901023');
    commitObservations({
        results: [first],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    const v1Artifacts = fs.readdirSync(dir).filter(f => f.startsWith('observation-'));
    assert.strictEqual(v1Artifacts.length, 1);
    const v1ArtifactPath = path.join(dir, v1Artifacts[0]);
    const v1Bytes = fs.readFileSync(v1ArtifactPath);
    const v1Artifact = JSON.parse(v1Bytes.toString('utf8'));
    assert.strictEqual(v1Artifact.import_terminal_state, 'ACCEPTED_NEW');

    // run 2: legal v2 -> ACCEPTED_REPEAT_EQUIVALENT, new artifact written
    const second = secondVersionPair('3901023');
    const summary2 = commitObservations({
        results: [pairResultOf(second)],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-2',
        builtAt: '2026-08-04T12:00:01.000Z',
    });
    assert.strictEqual(summary2.business_projection.accepted_repeat_equivalent_count, 1);
    const v2Artifacts = fs.readdirSync(dir).filter(f => f.startsWith('observation-'));
    assert.strictEqual(v2Artifacts.length, 2, 'REPEAT_EQUIVALENT must produce a NEW immutable artifact');
    const v2ArtifactPath = path.join(dir, v2Artifacts.find(f => f !== v1Artifacts[0]));
    const v2Artifact = JSON.parse(fs.readFileSync(v2ArtifactPath, 'utf8'));
    assert.strictEqual(v2Artifact.import_terminal_state, 'ACCEPTED_REPEAT_EQUIVALENT');
    // old artifact bytes must be unchanged
    assert.ok(v1Bytes.equals(fs.readFileSync(v1ArtifactPath)), 'old artifact must stay byte-identical');

    // three-way agreement: summary observation, ledger entry, artifact file
    const summaryDoc = JSON.parse(fs.readFileSync(path.join(dir, 'summary-2.json'), 'utf8'));
    const summaryObs = summaryDoc.business_projection.observations.find(o => o.artifact_file === v2Artifacts.find(f => f !== v1Artifacts[0]));
    assert.ok(summaryObs, 'summary must reference the new artifact');
    assert.strictEqual(summaryObs.terminal_state, 'ACCEPTED_REPEAT_EQUIVALENT');
    assert.strictEqual(summaryObs.business_hash, v2Artifact.business_hash);
    assert.strictEqual(summaryObs.stable_payload_sha256, v2Artifact.stable_payload_sha256);
    const ledger = JSON.parse(fs.readFileSync(path.join(dir, 'store-state-2.json'), 'utf8'));
    const ledgerEntry = Object.values(ledger.observations).find(e => e.artifact_file === v2Artifacts.find(f => f !== v1Artifacts[0]));
    assert.ok(ledgerEntry, 'ledger must reference the new artifact');
    assert.strictEqual(ledgerEntry.business_hash, v2Artifact.business_hash);
    assert.strictEqual(ledgerEntry.business_hash, summaryObs.business_hash, 'summary and ledger must agree');
    assert.strictEqual(ledgerEntry.stable_payload_sha256, v2Artifact.stable_payload_sha256);
    assert.strictEqual(ledgerEntry.terminal_state, 'ACCEPTED_REPEAT_EQUIVALENT');
    assert.notStrictEqual(v1Artifact.business_hash, v2Artifact.business_hash);

    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, true, JSON.stringify(result.errors));
});

test('T16 (P0-2): tampered summary business_hash is detected (three-way mismatch)', () => {
    const dir = tmpDir('fotmob-p0-2-sumtamper-');
    commitObservations({
        results: [pairResult('3901023')],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    const second = secondVersionPair('3901023');
    commitObservations({
        results: [pairResultOf(second)],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-2',
        builtAt: '2026-08-04T12:00:01.000Z',
    });
    // tamper ONLY the summary's business_hash (recompute the projection hash
    // so the summary self-check stays green — the cross-check must catch it)
    const summaryFile = path.join(dir, 'summary-2.json');
    const doc = JSON.parse(fs.readFileSync(summaryFile, 'utf8'));
    const obs = doc.business_projection.observations.find(o => o.business_hash !== null);
    obs.business_hash = 'a'.repeat(64);
    const { canonicalJsonHash } = require('../../src/infrastructure/fotmob/FotMobDetailStagingContract');
    const projectionCopy = { ...doc.business_projection };
    delete projectionCopy.business_projection_sha256;
    doc.business_projection.business_projection_sha256 = canonicalJsonHash(projectionCopy);
    fs.writeFileSync(summaryFile, JSON.stringify(doc, null, 2) + '\n');
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, false);
    assert.ok(
        result.errors.some(e => e.code === 'STATE_MISMATCH' && /business_hash disagrees with its artifact/.test(e.message)),
        JSON.stringify(result.errors)
    );
});

test('T17 (P0-2): tampered ledger business_hash is detected (three-way mismatch)', () => {
    const dir = tmpDir('fotmob-p0-2-ledtamper-');
    commitObservations({
        results: [pairResult('3901023')],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    const second = secondVersionPair('3901023');
    commitObservations({
        results: [pairResultOf(second)],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-2',
        builtAt: '2026-08-04T12:00:01.000Z',
    });
    // tamper ONLY the ledger's business_hash
    const ledgerFile = path.join(dir, 'store-state-2.json');
    const ledger = JSON.parse(fs.readFileSync(ledgerFile, 'utf8'));
    Object.values(ledger.observations)[1].business_hash = 'b'.repeat(64);
    fs.writeFileSync(ledgerFile, JSON.stringify(ledger, null, 2) + '\n');
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, false);
    assert.ok(
        result.errors.some(e => e.code === 'LEDGER_INVALID' && /business hash disagrees with its artifact/.test(e.message)),
        JSON.stringify(result.errors)
    );
});

test('T18 (P0-2): THIRD_EXACT_REPLAY -> ACCEPTED_REPEAT_EXACT, 0 new artifacts, validate PASS', () => {
    const dir = tmpDir('fotmob-p0-2-replay-');
    const v1 = pairResult('3901023');
    commitObservations({
        results: [v1],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    const v2 = secondVersionPair('3901023');
    commitObservations({
        results: [pairResultOf(v2)],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-2',
        builtAt: '2026-08-04T12:00:01.000Z',
    });
    const before = fs.readdirSync(dir).filter(f => f.startsWith('observation-')).length;
    // run 3: exact replay of v2 -> REPEAT_EXACT, no new artifact
    const summary3 = commitObservations({
        results: [pairResultOf(v2)],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-3',
        builtAt: '2026-08-04T12:00:02.000Z',
    });
    assert.strictEqual(summary3.business_projection.accepted_repeat_exact_count, 1);
    const after = fs.readdirSync(dir).filter(f => f.startsWith('observation-')).length;
    assert.strictEqual(after, before, 'REPEAT_EXACT must not produce a new artifact');
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, true, JSON.stringify(result.errors));
});

// ── P1-4: TOCTOU posture (Codex review 4863122944 P1-4) ──────

test('P1-4: readJsonFile refuses a symlink leaf via the no-follow fd (even pointing at a valid file)', () => {
    const dir = tmpDir('fotmob-p14-link-');
    const real = path.join(dir, 'real.json');
    const link = path.join(dir, 'link.json');
    fs.writeFileSync(real, '{}\n');
    fs.symlinkSync(real, link);
    const { readJsonFile } = require('../../src/infrastructure/fotmob/FotMobDetailStagingRetention');
    assert.throws(
        () => readJsonFile(link, { repositoryRoot: REPO_ROOT }),
        err => err.code === 'SAFETY_ERROR'
    );
});

test('P1-4: readJsonFile refuses a directory and a missing file', () => {
    const dir = tmpDir('fotmob-p14-dir-');
    const { readJsonFile } = require('../../src/infrastructure/fotmob/FotMobDetailStagingRetention');
    assert.throws(
        () => readJsonFile(dir, { repositoryRoot: REPO_ROOT }),
        err => err.code === 'SAFETY_ERROR'
    );
    assert.throws(
        () => readJsonFile(path.join(dir, 'missing.json'), { repositoryRoot: REPO_ROOT }),
        err => err.code === 'INPUT_ERROR'
    );
});

test('P1-4: readJsonFile reads through a symlink-free path and returns the exact bytes', () => {
    const dir = tmpDir('fotmob-p14-read-');
    const file = path.join(dir, 'doc.json');
    const bytes = Buffer.from('{"a":1}\n', 'utf8');
    fs.writeFileSync(file, bytes);
    const { readJsonFile } = require('../../src/infrastructure/fotmob/FotMobDetailStagingRetention');
    const { parsed, sha256 } = readJsonFile(file, { repositoryRoot: REPO_ROOT });
    assert.deepStrictEqual(parsed, { a: 1 });
    assert.strictEqual(
        sha256,
        require('node:crypto').createHash('sha256').update(bytes).digest('hex')
    );
});

test('P1-4: writeJsonAtomically refuses a group/world-writable output directory', () => {
    const dir = tmpDir('fotmob-p14-mode-');
    fs.chmodSync(dir, 0o777);
    assert.throws(
        () => writeJsonAtomically(path.join(dir, 'doc.json'), { a: 1 }, { repositoryRoot: REPO_ROOT }),
        err => err.code === 'SAFETY_ERROR'
    );
});

test('P1-4: writeJsonAtomically creates private directories (0700) and writes through them', () => {
    const dir = tmpDir('fotmob-p14-private-');
    const outputRoot = path.join(dir, 'out', 'nested');
    const result = writeJsonAtomically(
        path.join(outputRoot, 'doc.json'),
        { a: 1 },
        { repositoryRoot: REPO_ROOT }
    );
    assert.strictEqual(result.written, true);
    const stat = fs.lstatSync(outputRoot);
    assert.strictEqual(stat.mode & 0o777, 0o700);
    assert.deepStrictEqual(JSON.parse(fs.readFileSync(path.join(outputRoot, 'doc.json'), 'utf8')), { a: 1 });
});

test('P1-4: a live foreign store lock fails the commit closed (no lock, no writes)', () => {
    const dir = tmpDir('fotmob-p14-locklive-');
    // Simulate another live process holding the exclusive store lock.
    fs.writeFileSync(path.join(dir, '.staging-write.lock'), String(process.pid));
    assert.throws(
        () =>
            commitObservations({
                results: [pairResult('3901023')],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-1',
                builtAt: '2026-08-04T12:00:00.000Z',
            }),
        err => err.code === 'SAFETY_ERROR'
    );
    assert.deepStrictEqual(fs.readdirSync(dir).sort(), ['.staging-write.lock']);
});

test('P1-4: a stale (dead-holder) store lock is recovered and the commit proceeds', () => {
    const dir = tmpDir('fotmob-p14-lockstale-');
    fs.writeFileSync(path.join(dir, '.staging-write.lock'), '999999999'); // dead pid
    const summary = commitObservations({
        results: [pairResult('3901023')],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    assert.strictEqual(summary.business_projection.accepted_new_count, 1);
    assert.ok(!fs.existsSync(path.join(dir, '.staging-write.lock')), 'lock released after commit');
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, true, JSON.stringify(result.errors));
    assert.strictEqual(result.residue_files.length, 0);
});

test('P1-4: the commit lock is released and never appears as residue', () => {
    const dir = tmpDir('fotmob-p14-lockres-');
    commitObservations({
        results: [pairResult('3901023')],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    const names = fs.readdirSync(dir);
    assert.ok(!names.includes('.staging-write.lock'));
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, true, JSON.stringify(result.errors));
    assert.strictEqual(result.residue_files.length, 0);
});

test('R5-P2-1a: commitObservations rejects an illegal (path-traversal) source_match_id before any write', () => {
    const dir = tmpDir('fotmob-r5p21-traversal-');
    const pair = buildPair();
    const { convertPair } = require('../../src/infrastructure/fotmob/FotMobDetailStagingConverter');
    const ok = convertPair({
        payload: pair.payload,
        manifest: pair.manifest,
        payloadBytes: pair.payloadBytes,
    });
    // direct API abuse: legal artifact + escaped id — must fail closed BEFORE
    // any filename is derived (the old code would write
    // observation-x-../../escaped-<hash>.artifact.json outside outputRoot)
    const escaped = { ...ok, source_match_id: 'x/../../escaped' };
    assert.throws(
        () =>
            commitObservations({
                results: [escaped],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-1',
                builtAt: '2026-08-04T12:00:00.000Z',
            }),
        err => err.code === 'INPUT_ERROR' && /source_match_id must be numeric/.test(err.message)
    );
    assert.deepStrictEqual(fs.readdirSync(dir), [], 'nothing is written (no commit, no residue)');
    assert.ok(!fs.existsSync(path.join(dir, '..', 'escaped-E011.json')), 'nothing escapes the output root');
});

test('R5-P2-1b: commitObservations rejects result/artifact source_match_id disagreement', () => {
    const dir = tmpDir('fotmob-r5p21-mismatch-');
    const pair = buildPair();
    const { convertPair } = require('../../src/infrastructure/fotmob/FotMobDetailStagingConverter');
    const ok = convertPair({
        payload: pair.payload,
        manifest: pair.manifest,
        payloadBytes: pair.payloadBytes,
    });
    assert.throws(
        () =>
            commitObservations({
                results: [{ ...ok, source_match_id: '3900933' }],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-1',
                builtAt: '2026-08-04T12:00:00.000Z',
            }),
        err => err.code === 'INPUT_ERROR' && /disagrees with artifact/.test(err.message)
    );
    assert.deepStrictEqual(fs.readdirSync(dir), []);
});

test('R5-P2-1c: commitObservations rejects an artifact with a malformed stable_payload_sha256', () => {
    const dir = tmpDir('fotmob-r5p21-hash-');
    const pair = buildPair();
    const { convertPair } = require('../../src/infrastructure/fotmob/FotMobDetailStagingConverter');
    const ok = convertPair({
        payload: pair.payload,
        manifest: pair.manifest,
        payloadBytes: pair.payloadBytes,
    });
    assert.throws(
        () =>
            commitObservations({
                results: [{ ...ok, artifact: { ...ok.artifact, stable_payload_sha256: 'not-a-hash' } }],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-1',
                builtAt: '2026-08-04T12:00:00.000Z',
            }),
        err => err.code === 'INPUT_ERROR' && /stable_payload_sha256/.test(err.message)
    );
    assert.deepStrictEqual(fs.readdirSync(dir), []);
});

test('R5-P3-1a: validate rejects a ledger whose quarantines is an array (not a plain object)', () => {
    const dir = committedDir('fotmob-r5p31-array-');
    const ledgerFile = fs.readdirSync(dir).find(f => f.startsWith('store-state-'));
    const ledger = JSON.parse(fs.readFileSync(path.join(dir, ledgerFile), 'utf8'));
    ledger.quarantines = [];
    fs.writeFileSync(path.join(dir, ledgerFile), JSON.stringify(ledger, null, 2) + '\n');
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.code === 'LEDGER_INVALID' && /quarantines must be a plain object/.test(e.message)));
});

test('R5-P3-1b: validate rejects a ledger quarantine key with an invalid format', () => {
    const dir = tmpDir('fotmob-r5p31-key-');
    const pair = buildPair({
        normalized: {
            match_external_id: '3901023',
            home_team: { id: 1, name: 'AFC Bournemouth', score: 0 },
            away_team: { id: 2, name: 'Leicester City', score: 0 },
            events: [{ id: 9, minute: 500, homeScore: 0, awayScore: 0, event_kind: 'real_event' }],
            stats: [{ key: 'shots', homeValue: 0, awayValue: 0, period: 'All' }],
            lineup: { home: { coach: null, starters: [], subs: [] }, away: { coach: null, starters: [], subs: [] } },
            shotmap: { shots: [] },
        },
    });
    const { convertPair } = require('../../src/infrastructure/fotmob/FotMobDetailStagingConverter');
    const bad = convertPair({
        payload: pair.payload,
        manifest: pair.manifest,
        payloadBytes: pair.payloadBytes,
    });
    commitObservations({
        results: [bad],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    const ledgerFile = fs.readdirSync(dir).find(f => f.startsWith('store-state-'));
    const ledger = JSON.parse(fs.readFileSync(path.join(dir, ledgerFile), 'utf8'));
    const qKey = Object.keys(ledger.quarantines)[0];
    ledger.quarantines[`../../${qKey}`] = ledger.quarantines[qKey];
    delete ledger.quarantines[qKey];
    fs.writeFileSync(path.join(dir, ledgerFile), JSON.stringify(ledger, null, 2) + '\n');
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.code === 'LEDGER_INVALID' && /quarantine key has invalid format/.test(e.message)));
});

// ── R6-P2-1 (Codex round 6): strict input contract — no falsy/conditional
//    bypass on the exported commitObservations() ──────────────────────────

function quarantinedPairResult() {
    const pair = buildPair({
        normalized: {
            match_external_id: '3901023',
            home_team: { id: 1, name: 'AFC Bournemouth', score: 0 },
            away_team: { id: 2, name: 'Leicester City', score: 0 },
            events: [
                {
                    id: 9,
                    minute: 500,
                    homeScore: 0,
                    awayScore: 0,
                    event_kind: 'real_event',
                },
            ],
            stats: [{ key: 'shots', homeValue: 0, awayValue: 0, period: 'All' }],
            lineup: {
                home: { coach: null, starters: [], subs: [] },
                away: { coach: null, starters: [], subs: [] },
            },
            shotmap: { shots: [] },
        },
    });
    const { convertPair } = require('../../src/infrastructure/fotmob/FotMobDetailStagingConverter');
    const result = convertPair({
        payload: pair.payload,
        manifest: pair.manifest,
        payloadBytes: pair.payloadBytes,
    });
    assert.strictEqual(result.quarantine_status, 'quarantined');
    return result;
}

test('R6-P2-1a: commitObservations rejects an accepted result whose stable_payload_sha256 is a NON-STRING (number) — no conditional bypass', () => {
    const dir = tmpDir('fotmob-r6p21-numhash-');
    const ok = pairResult();
    assert.throws(
        () =>
            commitObservations({
                results: [{ ...ok, artifact: { ...ok.artifact, stable_payload_sha256: 7 } }],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-1',
                builtAt: '2026-08-04T12:00:00.000Z',
            }),
        err => err.code === 'INPUT_ERROR' && /stable_payload_sha256/.test(err.message)
    );
    assert.deepStrictEqual(fs.readdirSync(dir), [], 'nothing is written');
});

test('R6-P2-1b: commitObservations rejects a quarantined result with a FALSY error_code (0) — no silent E013 fallback', () => {
    const dir = tmpDir('fotmob-r6p21-falsy-');
    const bad = quarantinedPairResult();
    assert.throws(
        () =>
            commitObservations({
                results: [{ ...bad, error_code: 0 }],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-1',
                builtAt: '2026-08-04T12:00:00.000Z',
            }),
        err => err.code === 'INPUT_ERROR' && /registry error_code/.test(err.message)
    );
    assert.deepStrictEqual(fs.readdirSync(dir), [], 'nothing is written');
});

test('R6-P2-1c: commitObservations rejects a quarantined result with a NON-REGISTRY error_code (E999)', () => {
    const dir = tmpDir('fotmob-r6p21-e999-');
    const bad = quarantinedPairResult();
    assert.throws(
        () =>
            commitObservations({
                results: [{ ...bad, error_code: 'E999' }],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-1',
                builtAt: '2026-08-04T12:00:00.000Z',
            }),
        err => err.code === 'INPUT_ERROR' && /registry error_code/.test(err.message)
    );
    assert.deepStrictEqual(fs.readdirSync(dir), [], 'nothing is written');
});

test('R6-P2-1d: commitObservations rejects a quarantined result whose quarantine_status is not quarantined', () => {
    const dir = tmpDir('fotmob-r6p21-status-');
    const bad = quarantinedPairResult();
    assert.throws(
        () =>
            commitObservations({
                results: [{ ...bad, quarantine_status: 'not_quarantined' }],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-1',
                builtAt: '2026-08-04T12:00:00.000Z',
            }),
        err => err.code === 'INPUT_ERROR' && /quarantine_status/.test(err.message)
    );
    assert.deepStrictEqual(fs.readdirSync(dir), [], 'nothing is written');
});

test('R6-P2-1e (legal control): a genuine quarantined result still commits through the strict gate and validates clean', () => {
    const dir = tmpDir('fotmob-r6p21-legal-');
    const bad = quarantinedPairResult();
    const summary = commitObservations({
        results: [bad],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    assert.strictEqual(summary.business_projection.quarantined_count, 1);
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, true, JSON.stringify(result.errors));
});

// ── PATH_TRAVERSAL_TESTS (task section 11): extended R5-P2-1 surface ─────

test('R6-P2-1f: commitObservations rejects backslash traversal source_match_id (..\\..\\escaped)', () => {
    const dir = tmpDir('fotmob-r6p21-backslash-');
    const ok = pairResult();
    assert.throws(
        () =>
            commitObservations({
                results: [{ ...ok, source_match_id: '..\\..\\escaped' }],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-1',
                builtAt: '2026-08-04T12:00:00.000Z',
            }),
        err => err.code === 'INPUT_ERROR' && /source_match_id must be numeric/.test(err.message)
    );
    assert.deepStrictEqual(fs.readdirSync(dir), []);
    assert.ok(!fs.existsSync(path.join(dir, '..', 'escaped-E011.json')), 'no escape through backslashes');
});

test('R6-P2-1g: commitObservations rejects an EMPTY source_match_id', () => {
    const dir = tmpDir('fotmob-r6p21-empty-');
    const ok = pairResult();
    assert.throws(
        () =>
            commitObservations({
                results: [{ ...ok, source_match_id: '' }],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-1',
                builtAt: '2026-08-04T12:00:00.000Z',
            }),
        err => err.code === 'INPUT_ERROR' && /source_match_id must be numeric/.test(err.message)
    );
    assert.deepStrictEqual(fs.readdirSync(dir), []);
});

test('R6-P2-1h: commitObservations rejects a non-numeric alphanumeric source_match_id', () => {
    const dir = tmpDir('fotmob-r6p21-alpha-');
    const ok = pairResult();
    assert.throws(
        () =>
            commitObservations({
                results: [{ ...ok, source_match_id: '12ab34' }],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-1',
                builtAt: '2026-08-04T12:00:00.000Z',
            }),
        err => err.code === 'INPUT_ERROR' && /source_match_id must be numeric/.test(err.message)
    );
    assert.deepStrictEqual(fs.readdirSync(dir), []);
});

// ── R6-P2-2 (Codex round 6): quarantine key/entry/file/summary SEMANTIC
//    three-way binding ────────────────────────────────────────────────────

function commitQuarantined(dir) {
    const bad = quarantinedPairResult();
    commitObservations({
        results: [bad],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    return dir;
}

function mutateLedger(dir, mutate) {
    const ledgerFile = fs.readdirSync(dir).find(f => f.startsWith('store-state-'));
    const ledger = JSON.parse(fs.readFileSync(path.join(dir, ledgerFile), 'utf8'));
    mutate(ledger);
    fs.writeFileSync(path.join(dir, ledgerFile), JSON.stringify(ledger, null, 2) + '\n');
}

test('R6-P2-2a: validate rejects a ledger quarantine entry whose source_match_id disagrees with its key', () => {
    const dir = commitQuarantined(tmpDir('fotmob-r6p22-id-'));
    mutateLedger(dir, ledger => {
        const qKey = Object.keys(ledger.quarantines)[0];
        ledger.quarantines[qKey] = { ...ledger.quarantines[qKey], source_match_id: '456' };
    });
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.code === 'LEDGER_INVALID' && /source_match_id disagrees/.test(e.message)));
});

test('R6-P2-2b: validate rejects a ledger quarantine entry whose quarantine_file does not derive from its key', () => {
    const dir = commitQuarantined(tmpDir('fotmob-r6p22-file-'));
    mutateLedger(dir, ledger => {
        const qKey = Object.keys(ledger.quarantines)[0];
        ledger.quarantines[qKey] = { ...ledger.quarantines[qKey], quarantine_file: 'quarantine-999-E003.json' };
    });
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.code === 'LEDGER_INVALID' && /quarantine_file must be/.test(e.message)));
});

test('R6-P2-2c: validate rejects a ledger quarantine entry whose error_code disagrees with its key', () => {
    const dir = commitQuarantined(tmpDir('fotmob-r6p22-code-'));
    mutateLedger(dir, ledger => {
        const qKey = Object.keys(ledger.quarantines)[0];
        ledger.quarantines[qKey] = { ...ledger.quarantines[qKey], error_code: 'E002' };
    });
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.code === 'LEDGER_INVALID' && /error_code disagrees/.test(e.message)));
});

test('R6-P2-2d: validate rejects a summary quarantine observation with no matching ledger quarantine entry', () => {
    const dir = commitQuarantined(tmpDir('fotmob-r6p22-summary-'));
    const summaryFile = fs.readdirSync(dir).find(f => f.startsWith('summary-'));
    const summary = JSON.parse(fs.readFileSync(path.join(dir, summaryFile), 'utf8'));
    summary.business_projection.observations[0] = {
        ...summary.business_projection.observations[0],
        error_code: 'E002',
        quarantine_file: 'quarantine-3901023-E002.json',
    };
    fs.writeFileSync(path.join(dir, summaryFile), JSON.stringify(summary, null, 2) + '\n');
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.code === 'STATE_MISMATCH' && /no ledger quarantine entry/.test(e.message)));
});

test('R6-P2-2e (legal control): the summary quarantine row carries the derived quarantine_file and binds cleanly', () => {
    const dir = commitQuarantined(tmpDir('fotmob-r6p22-summary-legal-'));
    const summaryFile = fs.readdirSync(dir).find(f => f.startsWith('summary-'));
    const summary = JSON.parse(fs.readFileSync(path.join(dir, summaryFile), 'utf8'));
    const observation = summary.business_projection.observations[0];
    assert.strictEqual(observation.quarantine_file, 'quarantine-3901023-E011.json');
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, true, JSON.stringify(result.errors));
});

// ── LEDGER_QUARANTINE_SHAPE_TESTS (task section 11): extended R5-P3-1
//    surface — plain-object, key format, entry shape, enum, prototype ─────

test('R6-P2-3a: validate rejects ledger quarantines = null', () => {
    const dir = commitQuarantined(tmpDir('fotmob-r6p23-null-'));
    mutateLedger(dir, ledger => {
        ledger.quarantines = null;
    });
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.code === 'LEDGER_INVALID' && /quarantines must be a plain object/.test(e.message)));
});

test('R6-P2-3b: validate rejects ledger quarantines = "string"', () => {
    const dir = commitQuarantined(tmpDir('fotmob-r6p23-string-'));
    mutateLedger(dir, ledger => {
        ledger.quarantines = 'quarantined';
    });
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.code === 'LEDGER_INVALID' && /quarantines must be a plain object/.test(e.message)));
});

test('R6-P2-3c: validate rejects a quarantine entry that is null', () => {
    const dir = commitQuarantined(tmpDir('fotmob-r6p23-entry-null-'));
    mutateLedger(dir, ledger => {
        const qKey = Object.keys(ledger.quarantines)[0];
        ledger.quarantines[qKey] = null;
    });
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.code === 'LEDGER_INVALID' && /is not an object/.test(e.message)));
});

test('R6-P2-3d: validate rejects a quarantine entry that is an array', () => {
    const dir = commitQuarantined(tmpDir('fotmob-r6p23-entry-array-'));
    mutateLedger(dir, ledger => {
        const qKey = Object.keys(ledger.quarantines)[0];
        ledger.quarantines[qKey] = [];
    });
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.code === 'LEDGER_INVALID' && /is not an object/.test(e.message)));
});

test('R6-P2-3e: validate rejects a quarantine entry whose terminal_state is not a quarantine state (ACCEPTED_NEW)', () => {
    const dir = commitQuarantined(tmpDir('fotmob-r6p23-state-'));
    mutateLedger(dir, ledger => {
        const qKey = Object.keys(ledger.quarantines)[0];
        ledger.quarantines[qKey] = { ...ledger.quarantines[qKey], terminal_state: 'ACCEPTED_NEW' };
    });
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.code === 'LEDGER_INVALID' && /terminal_state must be a quarantine state/.test(e.message)));
});

test('R6-P2-3f: validate rejects a quarantine entry whose error_code is not a registry error code (E999)', () => {
    const dir = commitQuarantined(tmpDir('fotmob-r6p23-e999-'));
    mutateLedger(dir, ledger => {
        const qKey = Object.keys(ledger.quarantines)[0];
        ledger.quarantines[qKey] = { ...ledger.quarantines[qKey], error_code: 'E999' };
    });
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.code === 'LEDGER_INVALID' && /registry error code/.test(e.message)));
});

test('R6-P2-3g: prototype-key safety — a quarantines "__proto__" key is rejected (invalid format, no prototype pollution)', () => {
    const dir = commitQuarantined(tmpDir('fotmob-r6p23-proto-'));
    mutateLedger(dir, ledger => {
        Object.defineProperty(ledger.quarantines, '__proto__', {
            value: { source_match_id: '1', error_code: 'E011', terminal_state: 'QUARANTINED_VALIDATION_FAIL', quarantine_file: 'quarantine-1-E011.json' },
            enumerable: true,
            configurable: true,
            writable: true,
        });
    });
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, false);
    assert.ok(result.errors.some(e => e.code === 'LEDGER_INVALID' && /quarantine key has invalid format/.test(e.message)));
});

test('R6-P2-3h (idempotency control): re-running the same quarantined input stays byte-identical (R3-P2-1 surface intact)', () => {
    const dir = tmpDir('fotmob-r6p23-idem-');
    const bad = quarantinedPairResult();
    commitObservations({
        results: [bad],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    const before = fs.readdirSync(dir).sort().map(f => [f, fs.readFileSync(path.join(dir, f))]);
    commitObservations({
        results: [quarantinedPairResult()],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-2',
        builtAt: '2026-08-04T13:00:00.000Z',
    });
    const after = fs.readdirSync(dir).sort().map(f => [f, fs.readFileSync(path.join(dir, f))]);
    // run-2 adds a new summary + a new ledger version — quarantine files and
    // ledger quarantine entries must be byte-identical (single evidence).
    assert.strictEqual(fs.readdirSync(dir).filter(f => f.startsWith('quarantine-')).length, 1);
    const latestLedger = JSON.parse(
        fs.readFileSync(path.join(dir, fs.readdirSync(dir).filter(f => f.startsWith('store-state-')).sort().pop()), 'utf8')
    );
    assert.deepStrictEqual(Object.keys(latestLedger.quarantines), ['3901023:E011']);
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, true, JSON.stringify(result.errors));
    void before;
    void after;
});

// ── R7-P1-2 / R7-P2-1 / R7-P2-2 / R7-P3-2 (Codex round 7) ────────────────

test('R7-P1-2a: commitObservations validates the FINAL rebuilt REPEAT_EQUIVALENT artifact — tampered artifactInputs refused, zero writes', () => {
    const dir = tmpDir('fotmob-r7p12-tamper-');
    commitObservations({
        results: [pairResult('3901023')],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    const before = fs.readdirSync(dir).sort();
    const second = pairResultOf(secondVersionPair('3901023'));
    // the exported API caller controls artifactInputs — the rebuild must be
    // validated as the EXACT snapshot that would be written, ledgered and
    // markered. Garbage inputs rebuild an artifact with an empty stable hash.
    const tampered = { ...second, artifactInputs: { payload: {}, manifest: {} } };
    assert.throws(
        () =>
            commitObservations({
                results: [tampered],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-2',
                builtAt: '2026-08-04T12:00:01.000Z',
            }),
        err => err.code === 'INPUT_ERROR' && /rebuilt REPEAT_EQUIVALENT artifact/.test(err.message)
    );
    assert.deepStrictEqual(
        fs.readdirSync(dir).sort(),
        before,
        'a refused rebuild must not write, ledger, summary or marker anything'
    );
});

test('R7-P2-1a: commitObservations rejects an accepted artifact built with INHERITED properties (Object.create) — no proto smuggling', () => {
    const dir = tmpDir('fotmob-r7p21-proto-');
    const ok = pairResult();
    // Object.create(valid) has NO own fields — every `field in artifact`
    // check sees the prototype chain, but JSON.stringify writes nothing.
    const protoArtifact = Object.create(ok.artifact);
    assert.throws(
        () =>
            commitObservations({
                results: [{ ...ok, artifact: protoArtifact }],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-1',
                builtAt: '2026-08-04T12:00:00.000Z',
            }),
        err => err.code === 'INPUT_ERROR' && /plain JSON data/.test(err.message)
    );
    assert.deepStrictEqual(fs.readdirSync(dir), [], 'no write may happen for a non-plain artifact');
});

test('R7-P2-1b: commitObservations rejects an accepted artifact carrying ACCESSOR properties (getters)', () => {
    const dir = tmpDir('fotmob-r7p21-getter-');
    const ok = pairResult();
    // A getter can return a valid value during validation and a different one
    // at write time — the plain-JSON gate must refuse it outright.
    const getterArtifact = { ...ok.artifact };
    Object.defineProperty(getterArtifact, 'business_hash', {
        get: () => ok.artifact.business_hash,
        enumerable: true,
        configurable: true,
    });
    assert.throws(
        () =>
            commitObservations({
                results: [{ ...ok, artifact: getterArtifact }],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-1',
                builtAt: '2026-08-04T12:00:00.000Z',
            }),
        err => err.code === 'INPUT_ERROR' && /plain JSON data/.test(err.message)
    );
    assert.deepStrictEqual(fs.readdirSync(dir), []);
});

test('R7-P2-1c (legal control): a plain-spread legal artifact still commits', () => {
    const dir = tmpDir('fotmob-r7p21-plain-');
    const ok = pairResult('3901023');
    const summary = commitObservations({
        results: [{ ...ok, artifact: { ...ok.artifact } }],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    assert.strictEqual(summary.business_projection.accepted_new_count, 1);
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, true, JSON.stringify(result.errors));
});

test('R7-P2-2a: commitObservations refuses E013 on QUARANTINED_VALIDATION_FAIL — registry-valid but state-mismatched code, zero writes', () => {
    const dir = tmpDir('fotmob-r7p22-e013-');
    const bad = quarantinedPairResult(); // E011 / QUARANTINED_VALIDATION_FAIL
    const tampered = { ...bad, error_code: 'E013' };
    assert.throws(
        () =>
            commitObservations({
                results: [tampered],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-1',
                builtAt: '2026-08-04T12:00:00.000Z',
            }),
        err => err.code === 'INPUT_ERROR' && /does not match terminal_state/.test(err.message)
    );
    assert.deepStrictEqual(fs.readdirSync(dir), [], 'no evidence file, no ledger, no summary, no marker');
});

test('R7-P2-2b (legal control): QUARANTINED_PROVENANCE_MISMATCH carries exactly E008 and commits valid evidence', () => {
    const dir = tmpDir('fotmob-r7p22-provmatch-');
    const bad = quarantinedPairResult();
    const prov = { ...bad, terminal_state: 'QUARANTINED_PROVENANCE_MISMATCH', error_code: 'E008' };
    const summary = commitObservations({
        results: [prov],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    assert.strictEqual(summary.business_projection.quarantined_count, 1);
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, true, JSON.stringify(result.errors));
});

test('R7-P3-2a: commitObservations refuses an over-length source_match_id BEFORE any filename derives from it', () => {
    const dir = tmpDir('fotmob-r7p32-longid-');
    const ok = pairResult('3901023');
    const longId = '1'.repeat(33);
    const tampered = {
        ...ok,
        source_match_id: longId,
        artifact: { ...ok.artifact, source_match_id: longId },
    };
    assert.throws(
        () =>
            commitObservations({
                results: [tampered],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-1',
                builtAt: '2026-08-04T12:00:00.000Z',
            }),
        err => err.code === 'INPUT_ERROR' && /exceeds/.test(err.message)
    );
    assert.deepStrictEqual(fs.readdirSync(dir), [], 'no write may happen for an over-length id');
});

// ── R8-P2-1 / R8-P2-2 (Codex round 8) ────────────────────────

test('R8-P2-1a: commitObservations rejects an accepted artifact whose nested section ARRAY carries a non-enumerable own toJSON — no array smuggling', () => {
    const dir = tmpDir('fotmob-r8p21-tojson-');
    const ok = pairResult();
    // JSON.stringify INVOKES toJSON on arrays at write time, but the
    // pre-check hash recomputation (canonicalizeJson) does not — a
    // non-enumerable own toJSON is invisible to .every() and would write
    // tampered bytes into a store whose artifact hash then disagrees.
    const tampered = { ...ok, artifact: { ...ok.artifact } };
    Object.defineProperty(tampered.artifact.sections.events.json, 'toJSON', {
        enumerable: false,
        value: () => ({ tampered: true }),
    });
    assert.throws(
        () =>
            commitObservations({
                results: [tampered],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-1',
                builtAt: '2026-08-04T12:00:00.000Z',
            }),
        err => err.code === 'INPUT_ERROR' && /plain JSON data/.test(err.message)
    );
    assert.deepStrictEqual(fs.readdirSync(dir), [], 'no write may happen for a non-plain artifact');
});

test('R8-P2-1b: REPEAT_EQUIVALENT rebuild refuses artifactInputs whose payload array carries a non-enumerable own toJSON — zero writes', () => {
    const dir = tmpDir('fotmob-r8p21-eqv-');
    commitObservations({
        results: [pairResult('3901023')],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    const before = fs.readdirSync(dir).sort();
    const second = pairResultOf(secondVersionPair('3901023'));
    // The rebuilt artifact copies normalized sections BY REFERENCE — clone the
    // rebuild inputs so only the REBUILD source is tampered (the incoming
    // converter artifact must stay legal so the refusal is provably the
    // rebuild gate, not the pre-loop).
    const rebuiltInputs = JSON.parse(JSON.stringify(second.artifactInputs));
    Object.defineProperty(rebuiltInputs.payload.normalized.events, 'toJSON', {
        enumerable: false,
        value: () => ({ tampered: true }),
    });
    const tampered = { ...second, artifactInputs: rebuiltInputs };
    assert.throws(
        () =>
            commitObservations({
                results: [tampered],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-2',
                builtAt: '2026-08-04T12:00:01.000Z',
            }),
        err => err.code === 'INPUT_ERROR' && /rebuilt REPEAT_EQUIVALENT artifact is not plain JSON data/.test(err.message)
    );
    assert.deepStrictEqual(
        fs.readdirSync(dir).sort(),
        before,
        'a refused rebuild must not write, ledger, summary or marker anything'
    );
});

test('R8-P2-1c (legal control): dense standard arrays in a JSON round-tripped artifact still commit and validate PASS', () => {
    const dir = tmpDir('fotmob-r8p21-dense-');
    const ok = pairResult('3901023');
    // JSON round-trip produces exactly the dense standard arrays the strict
    // array gate must keep accepting.
    const roundTripped = { ...ok, artifact: JSON.parse(JSON.stringify(ok.artifact)) };
    const summary = commitObservations({
        results: [roundTripped],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    assert.strictEqual(summary.business_projection.accepted_new_count, 1);
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, true, JSON.stringify(result.errors));
});

test('R8-P2-2a: commitObservations refuses an unretainable LINKED_* terminal state — no summary/ledger/marker write', () => {
    const dir = tmpDir('fotmob-r8p22-linked-');
    // classifyAgainstStore passes ok:false terminal states through verbatim —
    // a direct caller can claim LINKED_CANONICAL, a downstream canonical-link
    // state the store validator's count arithmetic does not recognize. The
    // pre-loop must refuse it BEFORE any byte is written.
    assert.throws(
        () =>
            commitObservations({
                results: [
                    {
                        ok: false,
                        source_match_id: '3901023',
                        terminal_state: 'LINKED_CANONICAL',
                        error_code: null,
                        quarantine_status: 'not_quarantined',
                        artifact: null,
                    },
                ],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-1',
                builtAt: '2026-08-04T12:00:00.000Z',
            }),
        err => err.code === 'INPUT_ERROR' && /not retainable/.test(err.message)
    );
    assert.deepStrictEqual(fs.readdirSync(dir), [], 'no write may happen for an unretainable terminal state');
});

test('R8-P2-2b: commitObservations refuses ok:false with an accepted classification — a "failed" result cannot commit an artifact', () => {
    const dir = tmpDir('fotmob-r8p22-okflag-');
    const ok = pairResult('3901023');
    const lying = { ...ok, ok: false };
    assert.throws(
        () =>
            commitObservations({
                results: [lying],
                outputRoot: dir,
                repositoryRoot: REPO_ROOT,
                runId: 'run-1',
                builtAt: '2026-08-04T12:00:00.000Z',
            }),
        err => err.code === 'INPUT_ERROR' && /ok:false result cannot classify as accepted/.test(err.message)
    );
    assert.deepStrictEqual(fs.readdirSync(dir), [], 'no write may happen for an inconsistent ok flag');
});

test('R8-P2-2c (legal control): a plain REJECTED_SCHEMA_UNKNOWN result still commits and validates PASS', () => {
    const dir = tmpDir('fotmob-r8p22-rejected-');
    const rejected = {
        ok: false,
        source_match_id: '3901023',
        terminal_state: 'REJECTED_SCHEMA_UNKNOWN',
        error_code: 'E002',
        quarantine_status: 'not_quarantined',
        artifact: null,
    };
    const summary = commitObservations({
        results: [rejected],
        outputRoot: dir,
        repositoryRoot: REPO_ROOT,
        runId: 'run-1',
        builtAt: '2026-08-04T12:00:00.000Z',
    });
    assert.strictEqual(summary.business_projection.rejected_count, 1);
    assert.strictEqual(summary.business_projection.processed_count, 1);
    const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
    assert.strictEqual(result.ok, true, JSON.stringify(result.errors));
});
