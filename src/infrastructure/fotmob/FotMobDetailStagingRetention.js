"use strict";

// lifecycle: permanent
//
// FotMob detail staging — retention layer: atomic repository-external
// output and append-only snapshot semantics.
//
// The staging layer has NO database by design (this task): the "store" is
// the output directory itself plus a store-state.json ledger that records
// per-observation-key terminal states. Everything is a file, everything is
// atomic, nothing is ever updated in place:
//
//   - ACCEPTED_NEW             → new immutable artifact snapshot written
//   - ACCEPTED_REPEAT_EXACT    → identical key already staged; nothing written
//   - ACCEPTED_REPEAT_EQUIVALENT → same source_match_id, new payload version;
//                                new immutable snapshot, prior untouched
//   - REJECTED_*               → nothing written
//   - QUARANTINED_*            → lightweight quarantine evidence record
//                                (identity + error code; never full payload)
//
// Output safety (fail-closed):
//   - absolute path required; repository-internal paths rejected;
//   - symlink ancestors / symlink leaf rejected;
//   - output must never overwrite an input file;
//   - write → fsync → rename (same filesystem; tmp in the target directory);
//   - artifact + summary + store-state commit as both-or-neither: on any
//     failure the partial tmp files are removed and nothing appears final;
//   - existing file with identical bytes = idempotent success;
//   - existing file with different bytes = fail-closed (never overwrite);
//   - validate() detects partial output roots (artifacts without summary).

const path = require("node:path");
const fs = require("node:fs");
const crypto = require("node:crypto");

const {
  TERMINAL_STATES,
  ERROR_CODES,
  validateStagingArtifact,
  canonicalJsonHash,
} = require("./FotMobDetailStagingContract");

const STORE_STATE_SCHEMA = "fotmob-detail-staging-store-state/v1";

// ─────────────────────────────────────────────────────────────
// Path safety
// ─────────────────────────────────────────────────────────────

/**
 * Reject any symlink component in an absolute path (walking every ancestor —
 * an intermediate symlinked directory could redirect a write back into the
 * repository). Same discipline as the capture pipeline's path guards.
 */
/* eslint-disable-next-line complexity */
function assertNoSymlinkAncestors(absPath, fsImpl = fs) {
  const abs = path.resolve(String(absPath));
  const segments = abs.split(path.sep).filter(Boolean);
  let current = path.parse(abs).root;
  for (const segment of segments) {
    current = path.join(current, segment);
    let stat = null;
    try {
      stat = fsImpl.lstatSync(current);
    } catch {
      /* component absent is fine */
    }
    if (stat && stat.isSymbolicLink()) {
      throw Object.assign(
        new Error(`path component must not be a symlink: ${current}`),
        { code: "SAFETY_ERROR" },
      );
    }
  }
  return abs;
}

function ensureRealDirectoryTree(absDirPath, fsImpl = fs) {
  const abs = assertNoSymlinkAncestors(absDirPath, fsImpl);
  const segments = abs.split(path.sep).filter(Boolean);
  let current = path.parse(abs).root;
  for (const segment of segments) {
    current = path.join(current, segment);
    let stat = null;
    try {
      stat = fsImpl.lstatSync(current);
    } catch {
      /* absent */
    }
    if (stat) {
      if (stat.isSymbolicLink()) {
        throw Object.assign(
          new Error(`path component must not be a symlink: ${current}`),
          { code: "SAFETY_ERROR" },
        );
      }
      if (!stat.isDirectory()) {
        throw Object.assign(
          new Error(`path component must be a directory: ${current}`),
          { code: "SAFETY_ERROR" },
        );
      }
    } else {
      fsImpl.mkdirSync(current);
      let created = null;
      try {
        created = fsImpl.lstatSync(current);
      } catch {
        /* treat as missing */
      }
      if (!created || created.isSymbolicLink() || !created.isDirectory()) {
        throw Object.assign(
          new Error(`failed to create real directory: ${current}`),
          { code: "SAFETY_ERROR" },
        );
      }
    }
  }
  const finalStat = fsImpl.lstatSync(abs);
  if (!finalStat || finalStat.isSymbolicLink() || !finalStat.isDirectory()) {
    throw Object.assign(new Error(`target must be a real directory: ${abs}`), {
      code: "SAFETY_ERROR",
    });
  }
  return abs;
}

/**
 * Verify an output path is absolute, outside the repository, and has no
 * symlink component. Mirrors FotMobDetailCapturePlan.verifyRepositoryExternalPath.
 */
function verifyRepositoryExternalPath(outputPath, options = {}) {
  const repositoryRoot = options.repositoryRoot
    ? path.resolve(options.repositoryRoot)
    : path.resolve(__dirname, "..", "..", "..");
  if (!path.isAbsolute(String(outputPath || ""))) {
    throw Object.assign(new Error("output path must be absolute"), {
      code: "INPUT_ERROR",
    });
  }
  const abs = path.resolve(String(outputPath || ""));
  const repoResolved = path.resolve(repositoryRoot);
  const rel = path.relative(repoResolved, abs);
  if (rel === "" || (!rel.startsWith("..") && !path.isAbsolute(rel))) {
    throw Object.assign(
      new Error(`output path must be outside the repository: ${abs}`),
      { code: "SAFETY_ERROR" },
    );
  }
  assertNoSymlinkAncestors(abs);
  return abs;
}

// ─────────────────────────────────────────────────────────────
// Atomic write
// ─────────────────────────────────────────────────────────────

/**
 * Write a JSON document atomically: tmp file in the same directory (same
 * filesystem), write → fsync → close → rename. Existing files are never
 * overwritten unless identical (idempotency) — divergent content fails
 * closed.
 *
 * @param {string} filePath - final absolute path
 * @param {object} doc - JSON-serializable document
 * @param {object} options - { fsImpl, repositoryRoot }
 * @returns {{ written: boolean, reason: string }}
 */
/* eslint-disable-next-line complexity */
function writeJsonAtomically(filePath, doc, options = {}) {
  const fileSystem = options.fsImpl || fs;
  const abs = verifyRepositoryExternalPath(filePath, options);
  const dir = path.dirname(abs);
  ensureRealDirectoryTree(dir, fileSystem);

  let finalStat = null;
  try {
    finalStat = fileSystem.lstatSync(abs);
  } catch {
    /* absent */
  }
  if (finalStat && finalStat.isSymbolicLink()) {
    throw Object.assign(
      new Error(`refusing to write through a symlink: ${abs}`),
      { code: "SAFETY_ERROR" },
    );
  }

  const bytes = Buffer.from(JSON.stringify(doc, null, 2) + "\n", "utf8");
  const fileSha = crypto.createHash("sha256").update(bytes).digest("hex");

  if (finalStat && finalStat.isFile()) {
    const existing = fileSystem.readFileSync(abs);
    if (existing.equals(bytes)) {
      return { written: false, reason: "existing_identical" };
    }
    throw Object.assign(
      new Error(`refusing to overwrite divergent existing file: ${abs}`),
      { code: "OUTPUT_CONFLICT" },
    );
  }

  const tmp = `${abs}.tmp-${process.pid}`;
  // A stale tmp from a previous failed write must not block this one.
  try {
    fileSystem.unlinkSync(tmp);
  } catch {
    /* absent */
  }
  let fd;
  try {
    fd = fileSystem.openSync(tmp, "wx");
    try {
      fileSystem.writeSync(fd, bytes);
      fileSystem.fsyncSync(fd);
    } finally {
      fileSystem.closeSync(fd);
    }
    fileSystem.renameSync(tmp, abs);
  } catch (error) {
    // Never leave a seemingly-final file behind: remove the tmp and
    // rethrow so the caller sees the failure (both-or-neither).
    try {
      fileSystem.unlinkSync(tmp);
    } catch {
      /* best effort */
    }
    throw error;
  }
  return { written: true, reason: "written", sha256: fileSha };
}

function readJsonFile(filePath, options = {}) {
  const fileSystem = options.fsImpl || fs;
  const abs = path.resolve(String(filePath));
  let stat;
  try {
    stat = fileSystem.lstatSync(abs);
  } catch {
    throw Object.assign(new Error(`file not readable: ${abs}`), {
      code: "INPUT_ERROR",
    });
  }
  if (stat.isSymbolicLink() || !stat.isFile()) {
    throw Object.assign(
      new Error(`input must be a regular file, not a symlink: ${abs}`),
      { code: "SAFETY_ERROR" },
    );
  }
  const bytes = fileSystem.readFileSync(abs);
  let parsed;
  try {
    parsed = JSON.parse(bytes.toString("utf8"));
  } catch (error) {
    throw Object.assign(new Error(`file is not valid JSON: ${abs}`), {
      code: "INPUT_ERROR",
    });
  }
  return {
    parsed,
    bytes,
    sha256: crypto.createHash("sha256").update(bytes).digest("hex"),
  };
}

// ─────────────────────────────────────────────────────────────
// Snapshot store
// ─────────────────────────────────────────────────────────────

function observationKey(sourceMatchId, stablePayloadSha256) {
  return `${String(sourceMatchId)}:${String(stablePayloadSha256)}`;
}

function artifactFileName(sourceMatchId, stablePayloadSha256) {
  return `observation-${String(sourceMatchId)}-${String(stablePayloadSha256)}.artifact.json`;
}

function quarantineFileName(sourceMatchId, errorCode) {
  return `quarantine-${String(sourceMatchId)}-${String(errorCode)}.json`;
}

function summaryFileNameFor(runId) {
  // Plain-identifier run ids only: no slashes, no dot-leading segments.
  const safe = String(runId || "offline-staging-run").replace(
    /[^A-Za-z0-9._-]/g,
    "_",
  );
  return `summary-${safe}.json`;
}

function isSummaryFileName(name) {
  return /^summary-.*\.json$/.test(String(name || ""));
}

function emptyStoreState() {
  return {
    schema_version: STORE_STATE_SCHEMA,
    observations: {},
    quarantines: {},
  };
}

function loadStoreState(storeDir, options = {}) {
  const fileSystem = options.fsImpl || fs;
  const statePath = path.join(storeDir, "store-state.json");
  let stat = null;
  try {
    stat = fileSystem.lstatSync(statePath);
  } catch {
    /* absent */
  }
  if (!stat) return { state: emptyStoreState(), existed: false };
  const { parsed } = readJsonFile(statePath, options);
  if (
    !parsed ||
    parsed.schema_version !== STORE_STATE_SCHEMA ||
    !parsed.observations
  ) {
    throw Object.assign(
      new Error("store-state.json has an unsupported schema"),
      { code: "INPUT_ERROR" },
    );
  }
  return { state: parsed, existed: true };
}

/**
 * Classify the terminal state of one observation against the store (pure).
 *
 * @param {object} args - { result: convertPair result, storeState }
 * @returns {{ terminal_state: string, reason: string, artifact: object|null }}
 */
function classifyAgainstStore(args = {}) {
  const result = args.result;
  const storeState = args.storeState || emptyStoreState();
  // source_match_id comes from convertAll enrichment or, for direct
  // convertPair results, from the artifact document itself.
  const sourceMatchId = String(
    result.source_match_id ??
      (result.artifact && result.artifact.source_match_id) ??
      "",
  );
  const stable = String(
    (result.artifact && result.artifact.stable_payload_sha256) || "",
  );

  if (!result.ok) {
    if (result.quarantine_status === "quarantined") {
      return {
        terminal_state: result.terminal_state,
        reason: "quarantined",
        artifact: null,
      };
    }
    return {
      terminal_state: result.terminal_state,
      reason: "rejected",
      artifact: null,
    };
  }

  const key = observationKey(sourceMatchId, stable);
  if (storeState.observations[key]) {
    return {
      terminal_state: TERMINAL_STATES.ACCEPTED_REPEAT_EXACT,
      reason: "exact_duplicate",
      artifact: null,
    };
  }

  // Same source_match_id with a different payload version: identity must
  // agree with the previously staged observation, else fail closed.
  const prior = Object.values(storeState.observations).filter(
    (o) => String(o.source_match_id) === sourceMatchId,
  );
  if (prior.length > 0) {
    const artifact = result.artifact;
    const newIdentity = artifact.expected_identity || {};
    for (const p of prior) {
      if (
        canonicalJsonHash(p.expected_identity || {}) !==
        canonicalJsonHash(newIdentity)
      ) {
        return {
          terminal_state: TERMINAL_STATES.REJECTED_IDENTITY_INCONSISTENT,
          reason: "identity_conflict_with_staged_observation",
          artifact: null,
        };
      }
    }
    return {
      terminal_state: TERMINAL_STATES.ACCEPTED_REPEAT_EQUIVALENT,
      reason: "new_payload_version",
      artifact: result.artifact,
    };
  }

  return {
    terminal_state: TERMINAL_STATES.ACCEPTED_NEW,
    reason: "first_observation",
    artifact: result.artifact,
  };
}

// ─────────────────────────────────────────────────────────────
// Build orchestration
// ─────────────────────────────────────────────────────────────

/**
 * Stage converted observations into an output root with append-only snapshot
 * semantics and both-or-neither atomicity for (artifacts, summary,
 * store-state).
 *
 * @param {object} args - { results: convertPair results array, outputRoot,
 *                          storeDir, repositoryRoot, runId, fsImpl }
 * @returns {object} summary document
 */
/* eslint-disable-next-line complexity */
function commitObservations(args = {}) {
  const fileSystem = args.fsImpl || fs;
  const repositoryRoot =
    args.repositoryRoot || path.resolve(__dirname, "..", "..", "..");
  const outputRoot = verifyRepositoryExternalPath(args.outputRoot, {
    repositoryRoot,
    fsImpl: fileSystem,
  });
  const storeDir = verifyRepositoryExternalPath(
    args.storeDir || args.outputRoot,
    { repositoryRoot, fsImpl: fileSystem },
  );
  const runId = String(args.runId || "offline-staging-run");
  const results = Array.isArray(args.results) ? args.results : [];
  const builtAt = String(args.builtAt || "");

  ensureRealDirectoryTree(outputRoot, fileSystem);
  ensureRealDirectoryTree(storeDir, fileSystem);

  const { state: storeState } = loadStoreState(storeDir, {
    fsImpl: fileSystem,
  });

  // ── 1. classify every result against the store (pure, no writes) ──
  const classified = results.map((result) => ({
    result,
    classification: classifyAgainstStore({ result, storeState }),
  }));

  // ── 2. collect the writes to make ──
  const artifactWrites = [];
  const quarantineWrites = [];
  const newObservations = {};
  const quarantineEntries = [];
  // In-batch duplicate folding: the store starts from the persisted state,
  // so two identical results in ONE batch must not both classify as
  // ACCEPTED_NEW (that would write the same file twice). The second
  // occurrence folds to ACCEPTED_REPEAT_EXACT, order-independently.
  const newObservationKeys = new Set();
  for (const item of classified) {
    const result = item.result;
    const cls = item.classification;
    const sourceMatchId = String(
      result.source_match_id ??
        (result.artifact && result.artifact.source_match_id) ??
        "",
    );
    if (
      cls.terminal_state === TERMINAL_STATES.ACCEPTED_NEW ||
      cls.terminal_state === TERMINAL_STATES.ACCEPTED_REPEAT_EQUIVALENT
    ) {
      const artifact = cls.artifact;
      const key = observationKey(sourceMatchId, artifact.stable_payload_sha256);
      if (newObservationKeys.has(key)) {
        item.classification = {
          terminal_state: TERMINAL_STATES.ACCEPTED_REPEAT_EXACT,
          reason: "in_batch_duplicate",
          artifact: null,
        };
        continue;
      }
      newObservationKeys.add(key);
      const fileName = artifactFileName(
        sourceMatchId,
        artifact.stable_payload_sha256,
      );
      artifactWrites.push({ fileName, doc: artifact, key });
      newObservations[key] = {
        source_match_id: sourceMatchId,
        stable_payload_sha256: artifact.stable_payload_sha256,
        artifact_file: fileName,
        expected_identity: artifact.expected_identity,
        first_imported_at: String(artifact.generated_at),
      };
    } else if (
      cls.terminal_state === TERMINAL_STATES.QUARANTINED_VALIDATION_FAIL ||
      cls.terminal_state === TERMINAL_STATES.QUARANTINED_PROVENANCE_MISMATCH
    ) {
      const errorCode = result.error_code || ERROR_CODES.E013;
      const fileName = quarantineFileName(sourceMatchId, errorCode);
      const quarantineDoc = {
        schema_version: "fotmob-detail-staging-quarantine/v1",
        source_match_id: sourceMatchId,
        terminal_state: cls.terminal_state,
        error_code: errorCode,
        quarantine_status: "quarantined",
        quarantine_reason:
          result.errors && result.errors[0]
            ? result.errors[0].message
            : "validation fail",
        recorded_at: builtAt,
        // Evidence is the identity + error, never the full payload.
      };
      quarantineWrites.push({ fileName, doc: quarantineDoc });
      quarantineEntries.push({
        key: `${sourceMatchId}:${errorCode}`,
        entry: quarantineDoc,
      });
    }
  }

  // ── 3. stage everything in the same directory (same filesystem) ──
  const stagingDir = path.join(
    outputRoot,
    `.staging-${process.pid}-${Math.random().toString(36).slice(2, 8)}`,
  );
  ensureRealDirectoryTree(stagingDir, fileSystem);

  const nextStoreState = {
    schema_version: STORE_STATE_SCHEMA,
    observations: { ...storeState.observations, ...newObservations },
    quarantines: {
      ...(storeState.quarantines || {}),
      ...Object.fromEntries(quarantineEntries),
    },
  };

  const summary = buildSummary({
    classified,
    outputRoot,
    runId,
    builtAt,
    storeState: nextStoreState,
  });

  try {
    const staged = [];
    for (const w of artifactWrites) {
      const stagedPath = path.join(stagingDir, w.fileName);
      fileSystem.writeFileSync(
        stagedPath,
        JSON.stringify(w.doc, null, 2) + "\n",
        "utf8",
      );
      staged.push({
        fileName: w.fileName,
        finalPath: path.join(outputRoot, w.fileName),
      });
    }
    for (const w of quarantineWrites) {
      const stagedPath = path.join(stagingDir, w.fileName);
      fileSystem.writeFileSync(
        stagedPath,
        JSON.stringify(w.doc, null, 2) + "\n",
        "utf8",
      );
      staged.push({
        fileName: w.fileName,
        finalPath: path.join(storeDir, w.fileName),
      });
    }
    // Per-run summary: the run id names the file so two runs on the same
    // output root never collide (each run's summary carries its own
    // operations fields; the business projection is deterministic).
    const summaryFileName = summaryFileNameFor(runId);
    const summaryPath = path.join(stagingDir, summaryFileName);
    fileSystem.writeFileSync(
      summaryPath,
      JSON.stringify(summary, null, 2) + "\n",
      "utf8",
    );
    staged.push({
      fileName: summaryFileName,
      finalPath: path.join(outputRoot, summaryFileName),
    });
    const statePath = path.join(stagingDir, "store-state.json");
    fileSystem.writeFileSync(
      statePath,
      JSON.stringify(nextStoreState, null, 2) + "\n",
      "utf8",
    );
    staged.push({
      fileName: "store-state.json",
      finalPath: path.join(storeDir, "store-state.json"),
    });

    // ── 4. promote: verify-then-rename each file; conflicting existing
    //      final files fail closed and abort the commit. The store-state
    //      ledger is the ONE exception: it is an append-only account —
    //      every commit merges the persisted state with new observations,
    //      so its bytes legitimately change. Safety comes from the
    //      merge: existing keys must be preserved byte-for-byte in value
    //      (only new keys are added). ──
    for (const item of staged) {
      const finalPath = item.finalPath;
      let finalStat = null;
      try {
        finalStat = fileSystem.lstatSync(finalPath);
      } catch {
        /* absent */
      }
      if (finalStat && finalStat.isFile()) {
        if (item.fileName === "store-state.json") {
          const existing = JSON.parse(
            fileSystem.readFileSync(finalPath, "utf8"),
          );
          const next = nextStoreState;
          for (const [key, entry] of Object.entries(
            existing.observations || {},
          )) {
            if (
              JSON.stringify(next.observations[key]) !== JSON.stringify(entry)
            ) {
              throw Object.assign(
                new Error(
                  `refusing to rewrite existing store-state observation: ${key}`,
                ),
                { code: "OUTPUT_CONFLICT" },
              );
            }
          }
          // Ledger merge verified — allow the atomic replace.
        } else {
          const existing = fileSystem.readFileSync(finalPath);
          const stagedBytes = fileSystem.readFileSync(
            path.join(stagingDir, item.fileName),
          );
          if (existing.equals(stagedBytes)) {
            continue; // idempotent — byte-identical already present
          }
          throw Object.assign(
            new Error(
              `refusing to overwrite divergent existing output: ${finalPath}`,
            ),
            { code: "OUTPUT_CONFLICT" },
          );
        }
      }
      const tmpPath = path.join(stagingDir, item.fileName);
      const fd = fileSystem.openSync(tmpPath, "r");
      try {
        fileSystem.fsyncSync(fd);
      } finally {
        fileSystem.closeSync(fd);
      }
      fileSystem.renameSync(tmpPath, finalPath);
    }
  } catch (error) {
    // both-or-neither: remove the staging dir; already-renamed files are
    // complete artifacts (never partial), but the summary/store-state
    // missing means the root is incomplete — validate() will report it.
    try {
      fileSystem.rmSync(stagingDir, { recursive: true, force: true });
    } catch {
      /* best effort */
    }
    throw error;
  }
  try {
    fileSystem.rmSync(stagingDir, { recursive: true, force: true });
  } catch {
    /* best effort */
  }

  return summary;
}

/**
 * Build the deterministic summary document. Business projection (counts +
 * per-observation hashes) is byte-deterministic across identical inputs;
 * operations fields (runId, builtAt) are excluded from any business hash.
 */
/* eslint-disable-next-line complexity */
function buildSummary(args = {}) {
  const classified = args.classified || [];
  const outputRoot = args.outputRoot;
  const runId = String(args.runId || "");
  const builtAt = String(args.builtAt || "");
  const storeState = args.storeState || emptyStoreState();

  const terminalCounts = {};
  const observations = [];
  for (const item of classified) {
    const result = item.result;
    const cls = item.classification;
    const sourceMatchId = String(
      result.source_match_id ??
        (result.artifact && result.artifact.source_match_id) ??
        "",
    );
    const state = cls.terminal_state;
    terminalCounts[state] = (terminalCounts[state] || 0) + 1;
    const observation = {
      source_match_id: sourceMatchId,
      terminal_state: state,
      reason: cls.reason,
      error_code: result.error_code || null,
    };
    // Only the CLASSIFIED artifact (the one actually staged) is recorded —
    // a rejected or in-batch-folded result must not claim an artifact file.
    if (cls.artifact) {
      observation.stable_payload_sha256 = cls.artifact.stable_payload_sha256;
      observation.business_hash = cls.artifact.business_hash;
      observation.artifact_file = artifactFileName(
        sourceMatchId,
        cls.artifact.stable_payload_sha256,
      );
    }
    observations.push(observation);
  }
  observations.sort((a, b) => {
    if (a.source_match_id !== b.source_match_id) {
      return a.source_match_id < b.source_match_id ? -1 : 1;
    }
    return (a.stable_payload_sha256 || "") < (b.stable_payload_sha256 || "")
      ? -1
      : 1;
  });

  // ERRATA_3: the business projection must be byte-deterministic across
  // identical inputs — run-scoped values (paths, run ids, timestamps) live
  // in `operations` and never enter the projection or its hash.
  const businessProjection = {
    schema_version: "fotmob-detail-staging-summary/v1",
    processed_count: observations.length,
    accepted_new_count: terminalCounts[TERMINAL_STATES.ACCEPTED_NEW] || 0,
    accepted_repeat_exact_count:
      terminalCounts[TERMINAL_STATES.ACCEPTED_REPEAT_EXACT] || 0,
    accepted_repeat_equivalent_count:
      terminalCounts[TERMINAL_STATES.ACCEPTED_REPEAT_EQUIVALENT] || 0,
    rejected_count:
      (terminalCounts[TERMINAL_STATES.REJECTED_IDENTITY_INCONSISTENT] || 0) +
      (terminalCounts[TERMINAL_STATES.REJECTED_PROVENANCE_BROKEN] || 0) +
      (terminalCounts[TERMINAL_STATES.REJECTED_SCHEMA_UNKNOWN] || 0),
    quarantined_count:
      (terminalCounts[TERMINAL_STATES.QUARANTINED_VALIDATION_FAIL] || 0) +
      (terminalCounts[TERMINAL_STATES.QUARANTINED_PROVENANCE_MISMATCH] || 0),
    observations,
  };
  businessProjection.business_projection_sha256 =
    canonicalJsonHash(businessProjection);

  return {
    schema_version: "fotmob-detail-staging-summary/v1",
    business_projection: businessProjection,
    operations: {
      converter_run_id: runId,
      built_at: builtAt,
      output_root: String(outputRoot),
      store_observation_count: Object.keys(storeState.observations || {})
        .length,
    },
  };
}

// ─────────────────────────────────────────────────────────────
// Validate
// ─────────────────────────────────────────────────────────────

/**
 * Validate an output root: summary present (no partial state), store state
 * present, every artifact re-validated (schema + business hash + terminal
 * state coherence), every summary observation has its artifact file.
 */
/* eslint-disable-next-line complexity */
function validateOutputRoot(outputRoot, options = {}) {
  const fileSystem = options.fsImpl || fs;
  const repositoryRoot =
    options.repositoryRoot || path.resolve(__dirname, "..", "..", "..");
  const abs = verifyRepositoryExternalPath(outputRoot, {
    repositoryRoot,
    fsImpl: fileSystem,
  });
  const storeDir = options.storeDir
    ? verifyRepositoryExternalPath(options.storeDir, {
        repositoryRoot,
        fsImpl: fileSystem,
      })
    : abs;

  const errors = [];
  let summaries = [];
  let storeState = null;
  let summaryFiles = [];
  try {
    summaryFiles = fileSystem.readdirSync(abs).filter(isSummaryFileName).sort();
  } catch {
    errors.push({
      code: "PARTIAL_OUTPUT",
      message: "output root not readable",
    });
  }
  if (summaryFiles.length === 0) {
    errors.push({
      code: "PARTIAL_OUTPUT",
      message: "output root has no summary-*.json — partial/incomplete run",
    });
  }
  for (const summaryFile of summaryFiles) {
    try {
      summaries.push(
        readJsonFile(path.join(abs, summaryFile), { fsImpl: fileSystem })
          .parsed,
      );
    } catch (error) {
      errors.push({
        code: "PARTIAL_OUTPUT",
        message: `summary file unreadable: ${summaryFile}`,
      });
    }
  }
  try {
    storeState = readJsonFile(path.join(storeDir, "store-state.json"), {
      fsImpl: fileSystem,
    }).parsed;
  } catch {
    errors.push({
      code: "PARTIAL_OUTPUT",
      message: "store has no store-state.json",
    });
  }

  const artifactChecks = [];
  for (const summary of summaries) {
    if (
      !summary ||
      !summary.business_projection ||
      !Array.isArray(summary.business_projection.observations)
    ) {
      errors.push({
        code: "PARTIAL_OUTPUT",
        message: "summary has no business_projection.observations",
      });
      continue;
    }
    for (const observation of summary.business_projection.observations) {
      const artifactFile = observation.artifact_file;
      if (!artifactFile) {
        if (
          observation.terminal_state !== TERMINAL_STATES.ACCEPTED_REPEAT_EXACT
        ) {
          artifactChecks.push({
            source_match_id: observation.source_match_id,
            ok: false,
            error: "no artifact file recorded for non-repeat observation",
          });
        }
        continue;
      }
      try {
        const { parsed: artifact } = readJsonFile(
          path.join(abs, artifactFile),
          { fsImpl: fileSystem },
        );
        const validation = validateStagingArtifact(artifact);
        const stateCoherent =
          artifact.import_terminal_state === observation.terminal_state;
        artifactChecks.push({
          source_match_id: observation.source_match_id,
          ok: validation.ok && stateCoherent,
          error: validation.ok
            ? stateCoherent
              ? null
              : "terminal state mismatch vs summary"
            : validation.errors.join("; "),
          business_hash: artifact.business_hash,
        });
      } catch (error) {
        artifactChecks.push({
          source_match_id: observation.source_match_id,
          ok: false,
          error: error.message,
        });
      }
    }
  }

  const failed = artifactChecks.filter((c) => !c.ok);
  return {
    ok: errors.length === 0 && failed.length === 0,
    errors,
    artifact_checks: artifactChecks,
    artifact_check_count: artifactChecks.length,
    failed_artifact_check_count: failed.length,
    summary_present: summaries.length > 0,
    store_state_present: storeState !== null,
  };
}

module.exports = {
  STORE_STATE_SCHEMA,
  assertNoSymlinkAncestors,
  ensureRealDirectoryTree,
  verifyRepositoryExternalPath,
  writeJsonAtomically,
  readJsonFile,
  observationKey,
  artifactFileName,
  quarantineFileName,
  emptyStoreState,
  loadStoreState,
  classifyAgainstStore,
  commitObservations,
  buildSummary,
  validateOutputRoot,
};
