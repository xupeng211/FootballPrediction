"use strict";

// lifecycle: permanent
// CLI tests for scripts/ops/fotmob_detail_staging.js.
// Fully offline: no network (structurally forbidden), no database.

global.fetch = () => {
  throw new Error("REAL_NETWORK_FORBIDDEN_IN_TEST");
};

const { test } = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const {
  main,
  parseArgs,
  runBuild,
  runValidate,
  USAGE,
} = require("../../scripts/ops/fotmob_detail_staging");
const {
  buildPair,
  buildSourceIndex,
  sourceIndexEntry,
} = require("../helpers/fotmobDetailStagingFixtures");

const REPO_ROOT = path.resolve(__dirname, "..", "..");
const CLI_PATH = path.join(REPO_ROOT, "scripts/ops/fotmob_detail_staging.js");

function tmpDir(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

function writePair(dir, pair, sourceMatchId) {
  const payloadFile = path.join(dir, `${sourceMatchId}.payload.json`);
  const manifestFile = path.join(dir, `${sourceMatchId}.manifest.json`);
  fs.writeFileSync(payloadFile, pair.payloadBytes);
  fs.writeFileSync(manifestFile, JSON.stringify(pair.manifest, null, 2) + "\n");
  return { payloadFile, manifestFile };
}

// ── G. CLI / Make ───────────────────────────────────────────

test("G47: build without required args fails closed", async () => {
  await assert.rejects(
    () => runBuild({}),
    (err) => err.code === "INPUT_ERROR",
  );
  await assert.rejects(
    () => runBuild({ "source-index": "/tmp/x.json" }),
    (err) => err.code === "INPUT_ERROR",
  );
});

test("G48: help output states the offline boundary explicitly", () => {
  assert.match(USAGE, /OFFLINE ONLY/);
  assert.match(USAGE, /ZERO NETWORK/);
  assert.match(USAGE, /ZERO DATABASE/);
  assert.match(USAGE, /NO MIGRATION/);
  assert.match(USAGE, /NO CAPTURE/);
  assert.match(USAGE, /data-fotmob-detail-staging-/);
});

test("G49: build succeeds end-to-end (source index → artifacts + summary)", async () => {
  const dir = tmpDir("fotmob-cli-build-");
  const pair = buildPair();
  const { payloadFile, manifestFile } = writePair(dir, pair, "3901023");
  const index = buildSourceIndex([
    sourceIndexEntry("3901023", payloadFile, manifestFile),
  ]);
  const indexFile = path.join(dir, "source-index.json");
  fs.writeFileSync(indexFile, JSON.stringify(index, null, 2) + "\n");
  const outputRoot = path.join(dir, "out");

  const result = await runBuild({
    "source-index": indexFile,
    "output-root": outputRoot,
  });
  assert.strictEqual(result.status, "complete");
  assert.strictEqual(result.accepted_new_count, 1);
  assert.strictEqual(result.rejected_count, 0);
  assert.strictEqual(result.zero_network, true);
  assert.strictEqual(result.zero_database, true);
  assert.ok(
    fs
      .readdirSync(outputRoot)
      .some((f) => f.startsWith("summary-") && f.endsWith(".json")),
  );
  assert.strictEqual(
    fs.readdirSync(outputRoot).filter((f) => f.startsWith("observation-"))
      .length,
    1,
  );
});

test("G50: validate succeeds on a built output root", async () => {
  const dir = tmpDir("fotmob-cli-validate-");
  const pair = buildPair();
  const { payloadFile, manifestFile } = writePair(dir, pair, "3901023");
  const indexFile = path.join(dir, "source-index.json");
  fs.writeFileSync(
    indexFile,
    JSON.stringify(
      buildSourceIndex([
        sourceIndexEntry("3901023", payloadFile, manifestFile),
      ]),
      null,
      2,
    ) + "\n",
  );
  const outputRoot = path.join(dir, "out");
  await runBuild({ "source-index": indexFile, "output-root": outputRoot });

  const result = await runValidate({ "output-root": outputRoot });
  assert.strictEqual(result.status, "valid");
  assert.strictEqual(result.ok, true);
  assert.strictEqual(result.artifact_check_count, 1);
  assert.strictEqual(result.failed_artifact_check_count, 0);
});

test("G51: tampered artifact fails validate", async () => {
  const dir = tmpDir("fotmob-cli-tamper-");
  const pair = buildPair();
  const { payloadFile, manifestFile } = writePair(dir, pair, "3901023");
  const indexFile = path.join(dir, "source-index.json");
  fs.writeFileSync(
    indexFile,
    JSON.stringify(
      buildSourceIndex([
        sourceIndexEntry("3901023", payloadFile, manifestFile),
      ]),
      null,
      2,
    ) + "\n",
  );
  const outputRoot = path.join(dir, "out");
  const buildResult = await runBuild({
    "source-index": indexFile,
    "output-root": outputRoot,
  });
  const artifactFile =
    buildResult.accepted_new_count === 1
      ? fs.readdirSync(outputRoot).find((f) => f.startsWith("observation-"))
      : null;
  assert.ok(artifactFile);
  const artifactPath = path.join(outputRoot, artifactFile);
  const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
  artifact.business_hash = "1".repeat(64);
  fs.writeFileSync(artifactPath, JSON.stringify(artifact, null, 2) + "\n");

  const result = await runValidate({ "output-root": outputRoot });
  assert.strictEqual(result.status, "invalid");
  assert.strictEqual(result.ok, false);
});

test("G51b: single-artifact validate detects tampering", async () => {
  const dir = tmpDir("fotmob-cli-artifact-");
  const pair = buildPair();
  const { payloadFile, manifestFile } = writePair(dir, pair, "3901023");
  const indexFile = path.join(dir, "source-index.json");
  fs.writeFileSync(
    indexFile,
    JSON.stringify(
      buildSourceIndex([
        sourceIndexEntry("3901023", payloadFile, manifestFile),
      ]),
      null,
      2,
    ) + "\n",
  );
  const outputRoot = path.join(dir, "out");
  await runBuild({ "source-index": indexFile, "output-root": outputRoot });
  const artifactPath = path.join(
    outputRoot,
    fs.readdirSync(outputRoot).find((f) => f.startsWith("observation-")),
  );
  const clean = await runValidate({ artifact: artifactPath });
  assert.strictEqual(clean.status, "valid");
  const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
  artifact.business_hash = "2".repeat(64);
  fs.writeFileSync(artifactPath, JSON.stringify(artifact, null, 2) + "\n");
  const tampered = await runValidate({ artifact: artifactPath });
  assert.strictEqual(tampered.status, "invalid");
});

test("G52: Makefile staging targets contain no capture/network/DB commands", () => {
  const makefile = fs.readFileSync(path.join(REPO_ROOT, "Makefile"), "utf8");
  const start = makefile.indexOf("data-fotmob-detail-staging-help:");
  assert.ok(start !== -1, "data-fotmob-detail-staging-help target exists");
  // The block covers all three staging targets (help through validate).
  const end = makefile.indexOf("data-m3-canonical-inventory-preflight:", start);
  const block = makefile.slice(start, end === -1 ? makefile.length : end);
  // Command-level prohibition: the staging targets must not invoke the
  // capture pipeline, any network tool, any DB client, or the container.
  // (The literal phrase "NO CAPTURE" is required by the offline contract,
  // so the check targets commands, not substrings.)
  assert.doesNotMatch(
    block,
    /fotmob_detail_capture|curl|psql|pg_dump|pg_ctl|docker|playwright|compose/i,
  );
  assert.match(
    block,
    /OFFLINE ONLY|ZERO NETWORK|ZERO DATABASE|NO MIGRATION|NO CAPTURE/,
  );
  assert.match(block, /node scripts\/ops\/fotmob_detail_staging\.js build/);
  assert.match(block, /node scripts\/ops\/fotmob_detail_staging\.js validate/);
});

test("G52b: data-help lists the three staging targets as offline entries", () => {
  const makefile = fs.readFileSync(path.join(REPO_ROOT, "Makefile"), "utf8");
  const helpBlock = makefile.slice(makefile.indexOf("data-help:"));
  for (const target of [
    "data-fotmob-detail-staging-help",
    "data-fotmob-detail-staging-build",
    "data-fotmob-detail-staging-validate",
  ]) {
    assert.match(makefile, new RegExp(target));
  }
  assert.match(helpBlock, /fotmob-detail-staging/);
});

test("help subcommand and --help exit cleanly via main()", async () => {
  const help = await main(["help"]);
  assert.strictEqual(help, 0);
  const parsed = parseArgs(["--help"]);
  assert.strictEqual(parsed.args.help, true);
});

test("unknown subcommand fails closed", async () => {
  await assert.rejects(() => main(["explode"]), /unknown subcommand/);
});

test("spawned CLI prints JSON status and exits non-zero on error (no network/DB)", () => {
  const result = spawnSync(process.execPath, [CLI_PATH, "build"], {
    encoding: "utf8",
    timeout: 30000,
  });
  assert.notStrictEqual(result.status, 0);
  const parsed = JSON.parse(result.stdout);
  assert.strictEqual(parsed.status, "blocked");
  assert.strictEqual(parsed.zero_network, true);
  assert.strictEqual(parsed.zero_database, true);
});
