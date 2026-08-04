"use strict";

// lifecycle: permanent
// Retention tests for FotMobDetailStagingRetention.js — atomic output,
// append-only snapshot semantics, path safety.
// Fully offline: no network, no database.

global.fetch = () => {
  throw new Error("REAL_NETWORK_FORBIDDEN_IN_TEST");
};

const { test } = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const {
  verifyRepositoryExternalPath,
  writeJsonAtomically,
  observationKey,
  classifyAgainstStore,
  commitObservations,
  validateOutputRoot,
  emptyStoreState,
} = require("../../src/infrastructure/fotmob/FotMobDetailStagingRetention");
const {
  TERMINAL_STATES,
} = require("../../src/infrastructure/fotmob/FotMobDetailStagingContract");
const { buildPair } = require("../helpers/fotmobDetailStagingFixtures");

const REPO_ROOT = path.resolve(__dirname, "..", "..");

function tmpDir(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

function pairResult(sourceMatchId = "3901023") {
  const pair = buildPair({ source_match_id: sourceMatchId });
  const {
    convertPair,
  } = require("../../src/infrastructure/fotmob/FotMobDetailStagingConverter");
  return convertPair({
    payload: pair.payload,
    manifest: pair.manifest,
    payloadBytes: pair.payloadBytes,
  });
}

// ── path safety ─────────────────────────────────────────────

test("E32: repository-internal output paths are rejected", () => {
  assert.throws(
    () =>
      verifyRepositoryExternalPath(path.join(REPO_ROOT, "out"), {
        repositoryRoot: REPO_ROOT,
      }),
    (err) => err.code === "SAFETY_ERROR",
  );
  assert.throws(
    () =>
      verifyRepositoryExternalPath(REPO_ROOT, { repositoryRoot: REPO_ROOT }),
    (err) => err.code === "SAFETY_ERROR",
  );
  assert.throws(
    () =>
      verifyRepositoryExternalPath("relative/path", {
        repositoryRoot: REPO_ROOT,
      }),
    (err) => err.code === "INPUT_ERROR",
  );
});

test("E33: symlinked output components are rejected", () => {
  const dir = tmpDir("fotmob-ret-symlink-");
  const real = path.join(dir, "real");
  const link = path.join(dir, "link");
  fs.mkdirSync(real);
  fs.symlinkSync(real, link);
  assert.throws(
    () =>
      verifyRepositoryExternalPath(path.join(link, "out"), {
        repositoryRoot: REPO_ROOT,
      }),
    (err) => err.code === "SAFETY_ERROR",
  );
});

test("E33b: symlinked input files are rejected by readJsonFile", () => {
  const dir = tmpDir("fotmob-ret-symlink-input-");
  const real = path.join(dir, "real.json");
  const link = path.join(dir, "link.json");
  fs.writeFileSync(real, "{}");
  fs.symlinkSync(real, link);
  const {
    readJsonFile,
  } = require("../../src/infrastructure/fotmob/FotMobDetailStagingRetention");
  assert.throws(
    () => readJsonFile(link),
    (err) => err.code === "SAFETY_ERROR",
  );
});

// ── atomic writes / idempotency ─────────────────────────────

test("E34: write → identical rewrite is idempotent (nothing rewritten)", () => {
  const dir = tmpDir("fotmob-ret-atomic-");
  const file = path.join(dir, "doc.json");
  const doc = { a: 1, nested: { b: [1, 2, 3] } };
  const first = writeJsonAtomically(file, doc, { repositoryRoot: REPO_ROOT });
  assert.strictEqual(first.written, true);
  const second = writeJsonAtomically(file, doc, { repositoryRoot: REPO_ROOT });
  assert.strictEqual(second.written, false);
  assert.strictEqual(second.reason, "existing_identical");
  // no tmp residue
  assert.strictEqual(fs.readdirSync(dir).length, 1);
});

test("E35: divergent existing file fails closed (never overwritten)", () => {
  const dir = tmpDir("fotmob-ret-divergent-");
  const file = path.join(dir, "doc.json");
  writeJsonAtomically(file, { a: 1 }, { repositoryRoot: REPO_ROOT });
  assert.throws(
    () => writeJsonAtomically(file, { a: 2 }, { repositoryRoot: REPO_ROOT }),
    (err) => err.code === "OUTPUT_CONFLICT",
  );
  assert.strictEqual(JSON.parse(fs.readFileSync(file, "utf8")).a, 1);
});

test("E38: fault injection on rename leaves no staged residue (both-or-neither)", () => {
  const dir = tmpDir("fotmob-ret-fault-");
  const file = path.join(dir, "doc.json");
  const failingFs = {
    ...fs,
    renameSync: () => {
      throw new Error("injected rename failure");
    },
  };
  assert.throws(() =>
    writeJsonAtomically(
      file,
      { a: 1 },
      { repositoryRoot: REPO_ROOT, fsImpl: failingFs },
    ),
  );
  assert.deepStrictEqual(fs.readdirSync(dir), []);
});

// ── snapshot semantics (store) ──────────────────────────────

test("C20: exact duplicate folds to ACCEPTED_REPEAT_EXACT and writes nothing", () => {
  const store = emptyStoreState();
  const r1 = pairResult("3901023");
  const first = classifyAgainstStore({ result: r1, storeState: store });
  assert.strictEqual(first.terminal_state, TERMINAL_STATES.ACCEPTED_NEW);
  store.observations[
    observationKey("3901023", r1.artifact.stable_payload_sha256)
  ] = {
    source_match_id: "3901023",
    stable_payload_sha256: r1.artifact.stable_payload_sha256,
    expected_identity: r1.artifact.expected_identity,
  };
  const second = classifyAgainstStore({ result: r1, storeState: store });
  assert.strictEqual(
    second.terminal_state,
    TERMINAL_STATES.ACCEPTED_REPEAT_EXACT,
  );
  assert.strictEqual(second.artifact, null); // nothing new written
});

test("C22/C23: same match, new payload version → new immutable snapshot; old untouched", () => {
  const dir = tmpDir("fotmob-ret-versions-");
  const storeDir = path.join(dir, "store");
  const outputRoot = path.join(dir, "out");

  const v1 = pairResult("3901023");
  const summary1 = commitObservations({
    results: [v1],
    outputRoot,
    storeDir,
    repositoryRoot: REPO_ROOT,
    runId: "run-1",
    builtAt: "2026-08-04T12:00:00.000Z",
  });
  assert.strictEqual(summary1.business_projection.accepted_new_count, 1);
  const artifactFile1 =
    summary1.business_projection.observations[0].artifact_file;
  const bytes1 = fs.readFileSync(path.join(outputRoot, artifactFile1));
  const hash1 = JSON.parse(bytes1).business_hash;

  // v2: same identity, modified event (legal re-observation, re-signed).
  const {
    buildPayload,
    buildManifest,
  } = require("../helpers/fotmobDetailStagingFixtures");
  const norm = buildPayload({ source_match_id: "3901023" }).normalized;
  norm.events = [
    {
      id: 9434327,
      minute: 11,
      homeScore: 0,
      awayScore: 0,
      event_kind: "real_event",
    },
  ];
  const payloadV2 = buildPayload({
    source_match_id: "3901023",
    normalized: norm,
  });
  const bytesV2 = Buffer.from(
    JSON.stringify(payloadV2, null, 2) + "\n",
    "utf8",
  );
  const manifestV2 = buildManifest(payloadV2);
  const {
    convertPair,
  } = require("../../src/infrastructure/fotmob/FotMobDetailStagingConverter");
  const v2 = convertPair({
    payload: payloadV2,
    manifest: manifestV2,
    payloadBytes: bytesV2,
  });
  assert.strictEqual(v2.ok, true);
  assert.notStrictEqual(
    v2.artifact.stable_payload_sha256,
    v1.artifact.stable_payload_sha256,
  );

  const summary2 = commitObservations({
    results: [v1, v2],
    outputRoot,
    storeDir,
    repositoryRoot: REPO_ROOT,
    runId: "run-2",
    builtAt: "2026-08-04T12:00:01.000Z",
  });
  assert.strictEqual(
    summary2.business_projection.accepted_repeat_exact_count,
    1,
  );
  assert.strictEqual(
    summary2.business_projection.accepted_repeat_equivalent_count,
    1,
  );
  // old snapshot bytes unchanged
  const bytes1After = fs.readFileSync(path.join(outputRoot, artifactFile1));
  assert.ok(bytes1After.equals(bytes1));
  assert.strictEqual(JSON.parse(bytes1After).business_hash, hash1);
});

test("C24: identity conflict with a staged observation fails closed (never overwrites)", () => {
  const dir = tmpDir("fotmob-ret-conflict-");
  const storeDir = path.join(dir, "store");
  const outputRoot = path.join(dir, "out");

  const v1 = pairResult("3901023");
  commitObservations({
    results: [v1],
    outputRoot,
    storeDir,
    repositoryRoot: REPO_ROOT,
    runId: "run-1",
    builtAt: "2026-08-04T12:00:00.000Z",
  });

  // same source id, different teams: the payload must be internally
  // self-consistent (expected == observed, re-signed) so it passes
  // conversion — the conflict is with the ALREADY STAGED observation, and
  // must be caught by the store, not by payload validation.
  const pairConflict = buildPair({
    source_match_id: "3901023",
    expected: { home_team: "Tottenham Hotspur", away_team: "Arsenal" },
    observed: { home_team: "Tottenham Hotspur", away_team: "Arsenal" },
  });
  const {
    convertPair,
  } = require("../../src/infrastructure/fotmob/FotMobDetailStagingConverter");
  const conflict = convertPair({
    payload: pairConflict.payload,
    manifest: pairConflict.manifest,
    payloadBytes: pairConflict.payloadBytes,
  });
  assert.strictEqual(
    conflict.ok,
    true,
    "conflict payload must be self-consistent and pass conversion",
  );
  const summary = commitObservations({
    results: [conflict],
    outputRoot,
    storeDir,
    repositoryRoot: REPO_ROOT,
    runId: "run-2",
    builtAt: "2026-08-04T12:00:02.000Z",
  });
  const obs = summary.business_projection.observations.find(
    (o) => o.source_match_id === "3901023",
  );
  assert.strictEqual(
    obs.terminal_state,
    TERMINAL_STATES.REJECTED_IDENTITY_INCONSISTENT,
  );
  assert.strictEqual(obs.reason, "identity_conflict_with_staged_observation");
});

test("C25: provenance conflict (tampered payload) is rejected and writes nothing", () => {
  const dir = tmpDir("fotmob-ret-provenance-");
  const storeDir = path.join(dir, "store");
  const outputRoot = path.join(dir, "out");

  const pair = buildPair();
  const {
    convertPair,
  } = require("../../src/infrastructure/fotmob/FotMobDetailStagingConverter");
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
    storeDir,
    repositoryRoot: REPO_ROOT,
    runId: "run-1",
    builtAt: "2026-08-04T12:00:00.000Z",
  });
  assert.strictEqual(summary.business_projection.accepted_new_count, 0);
  assert.strictEqual(summary.business_projection.rejected_count, 1);
  assert.deepStrictEqual(
    fs.readdirSync(outputRoot).filter((f) => f.startsWith("observation-")),
    [],
  );
});

test("quarantine observations write lightweight evidence records (never full payload)", () => {
  const dir = tmpDir("fotmob-ret-quarantine-");
  const storeDir = path.join(dir, "store");
  const outputRoot = path.join(dir, "out");

  const pair = buildPair({
    normalized: {
      match_external_id: "3901023",
      home_team: { id: 1, name: "AFC Bournemouth", score: 0 },
      away_team: { id: 2, name: "Leicester City", score: 0 },
      events: [
        {
          id: 9,
          minute: 500,
          homeScore: 0,
          awayScore: 0,
          event_kind: "real_event",
        },
      ],
      stats: [{ key: "shots", homeValue: 0, awayValue: 0, period: "All" }],
      lineup: {
        home: { coach: null, starters: [], subs: [] },
        away: { coach: null, starters: [], subs: [] },
      },
      shotmap: { shots: [] },
    },
  });
  const {
    convertPair,
  } = require("../../src/infrastructure/fotmob/FotMobDetailStagingConverter");
  const result = convertPair({
    payload: pair.payload,
    manifest: pair.manifest,
    payloadBytes: pair.payloadBytes,
  });
  assert.strictEqual(result.quarantine_status, "quarantined");
  const summary = commitObservations({
    results: [result],
    outputRoot,
    storeDir,
    repositoryRoot: REPO_ROOT,
    runId: "run-1",
    builtAt: "2026-08-04T12:00:00.000Z",
  });
  assert.strictEqual(summary.business_projection.quarantined_count, 1);
  const quarantineFiles = fs
    .readdirSync(storeDir)
    .filter((f) => f.startsWith("quarantine-"));
  assert.strictEqual(quarantineFiles.length, 1);
  const evidence = JSON.parse(
    fs.readFileSync(path.join(storeDir, quarantineFiles[0]), "utf8"),
  );
  assert.strictEqual(evidence.error_code, "E011");
  assert.ok(!JSON.stringify(evidence).includes("normalized"));
});

test("C27: terminal state arithmetic is consistent across the summary", () => {
  const dir = tmpDir("fotmob-ret-arithmetic-");
  const storeDir = path.join(dir, "store");
  const outputRoot = path.join(dir, "out");

  const pair = buildPair();
  const {
    convertPair,
  } = require("../../src/infrastructure/fotmob/FotMobDetailStagingConverter");
  const ok = convertPair({
    payload: pair.payload,
    manifest: pair.manifest,
    payloadBytes: pair.payloadBytes,
  });
  const bad = convertPair({
    payload: { ...pair.payload, season: "1999" },
    manifest: pair.manifest,
    payloadBytes: pair.payloadBytes,
  });
  const summary = commitObservations({
    results: [ok, ok, bad],
    outputRoot,
    storeDir,
    repositoryRoot: REPO_ROOT,
    runId: "run-1",
    builtAt: "2026-08-04T12:00:00.000Z",
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
    bp.processed_count,
  );
});

// ── validate output root ────────────────────────────────────

test("E36: artifact-only residue (missing summary) is detected as partial output", () => {
  const dir = tmpDir("fotmob-ret-partial-");
  fs.writeFileSync(path.join(dir, "observation-1-abc.artifact.json"), "{}");
  const result = validateOutputRoot(dir, { repositoryRoot: REPO_ROOT });
  assert.strictEqual(result.ok, false);
  assert.ok(result.errors.some((e) => e.code === "PARTIAL_OUTPUT"));
});

test("E37: full commit validates green end-to-end", () => {
  const dir = tmpDir("fotmob-ret-validate-");
  const storeDir = path.join(dir, "store");
  const outputRoot = path.join(dir, "out");
  commitObservations({
    results: [pairResult("3901023")],
    outputRoot,
    storeDir,
    repositoryRoot: REPO_ROOT,
    runId: "run-1",
    builtAt: "2026-08-04T12:00:00.000Z",
  });
  const result = validateOutputRoot(outputRoot, {
    storeDir,
    repositoryRoot: REPO_ROOT,
  });
  assert.strictEqual(
    result.ok,
    true,
    JSON.stringify({
      errors: result.errors,
      failed: result.failed_artifact_check_count,
    }),
  );
  assert.strictEqual(result.artifact_check_count, 1);
  assert.strictEqual(result.summary_present, true);
});

test("tampered artifact file after commit is detected by validate", () => {
  const dir = tmpDir("fotmob-ret-tamper-");
  const storeDir = path.join(dir, "store");
  const outputRoot = path.join(dir, "out");
  const summary = commitObservations({
    results: [pairResult("3901023")],
    outputRoot,
    storeDir,
    repositoryRoot: REPO_ROOT,
    runId: "run-1",
    builtAt: "2026-08-04T12:00:00.000Z",
  });
  const artifactFile =
    summary.business_projection.observations[0].artifact_file;
  const artifact = JSON.parse(
    fs.readFileSync(path.join(outputRoot, artifactFile), "utf8"),
  );
  artifact.business_hash = "0".repeat(64);
  fs.writeFileSync(
    path.join(outputRoot, artifactFile),
    JSON.stringify(artifact, null, 2) + "\n",
  );
  const result = validateOutputRoot(outputRoot, {
    storeDir,
    repositoryRoot: REPO_ROOT,
  });
  assert.strictEqual(result.ok, false);
  assert.strictEqual(result.failed_artifact_check_count, 1);
});

test("summary business projection is deterministic across identical inputs", () => {
  const dir = tmpDir("fotmob-ret-det-");
  const s1 = commitObservations({
    results: [pairResult("3901023")],
    outputRoot: path.join(dir, "out1"),
    storeDir: path.join(dir, "store1"),
    repositoryRoot: REPO_ROOT,
    runId: "run-1",
    builtAt: "2026-08-04T12:00:00.000Z",
  });
  const s2 = commitObservations({
    results: [pairResult("3901023")],
    outputRoot: path.join(dir, "out2"),
    storeDir: path.join(dir, "store2"),
    repositoryRoot: REPO_ROOT,
    runId: "run-2",
    builtAt: "2026-08-04T12:00:05.000Z",
  });
  assert.strictEqual(
    s1.business_projection.business_projection_sha256,
    s2.business_projection.business_projection_sha256,
  );
  // operations fields differ, business projection does not (ERRATA_3)
  assert.notStrictEqual(
    s1.operations.converter_run_id,
    s2.operations.converter_run_id,
  );
});
