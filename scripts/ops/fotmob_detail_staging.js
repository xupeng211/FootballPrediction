#!/usr/bin/env node
"use strict";

// lifecycle: permanent
// Internal Node CLI for the offline FotMob detail staging converter /
// validator. The canonical operator surface is the Make targets
// data-fotmob-detail-staging-{help,build,validate}; this CLI is the engine.
//
// OFFLINE ONLY — ZERO NETWORK — ZERO DATABASE — NO MIGRATION — NO CAPTURE.
//
// The tool structurally cannot fetch (no fetcher import, no fetch/http
// usage), cannot connect to a database (no pg/ioredis import, no env DB
// variables), and ignores any NETWORK_AUTHORIZATION / DB_WRITE_AUTHORIZATION
// / capture authorization variables by design. Inputs and outputs are
// repository-external absolute paths only.

const path = require("node:path");

const {
  validateSourceIndex,
  validateStagingArtifact,
  ERROR_CODES,
} = require("../../src/infrastructure/fotmob/FotMobDetailStagingContract");
const {
  convertAll,
} = require("../../src/infrastructure/fotmob/FotMobDetailStagingConverter");
const {
  readJsonFile,
  verifyRepositoryExternalPath,
  commitObservations,
  validateOutputRoot,
} = require("../../src/infrastructure/fotmob/FotMobDetailStagingRetention");

const USAGE = [
  "Usage:",
  "  node scripts/ops/fotmob_detail_staging.js build \\",
  "    --source-index=/absolute/external/path/source-index.json \\",
  "    --output-root=/absolute/external/path/out \\",
  "    [--store-dir=/absolute/external/path/store] \\",
  "    [--run-id=<plain-identifier>]",
  "",
  "  node scripts/ops/fotmob_detail_staging.js validate \\",
  "    --output-root=/absolute/external/path/out \\",
  "    [--store-dir=/absolute/external/path/store]",
  "",
  "  node scripts/ops/fotmob_detail_staging.js validate \\",
  "    --artifact=/absolute/external/path/observation-<id>-<hash>.artifact.json",
  "",
  "  node scripts/ops/fotmob_detail_staging.js help",
  "",
  "Safety:",
  "  OFFLINE ONLY — ZERO NETWORK — ZERO DATABASE — NO MIGRATION — NO CAPTURE",
  "  No authorization environment variable is read; fetch and DB access are",
  "  structurally impossible from this tool.",
  "  All inputs and outputs must be absolute paths OUTSIDE the repository;",
  "  symlinks are rejected; existing divergent outputs fail closed.",
  "  Canonical operator entry: make data-fotmob-detail-staging-{help,build,validate}.",
].join("\n");

function parseArgs(argv) {
  const args = {};
  const positionals = [];
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (token === "--help" || token === "-h") {
      args.help = true;
      continue;
    }
    if (token.startsWith("--")) {
      const eq = token.indexOf("=");
      const rawKey = eq === -1 ? token.slice(2) : token.slice(2, eq);
      let value;
      if (eq !== -1) {
        value = token.slice(eq + 1);
      } else {
        const next = argv[i + 1];
        if (next !== undefined && !next.startsWith("--")) {
          value = next;
          i += 1;
        } else {
          value = "";
        }
      }
      args[rawKey] = value;
    } else {
      positionals.push(token);
    }
  }
  return { args, positionals };
}

function print(value) {
  process.stdout.write(`${JSON.stringify(value)}\n`);
}

function builtAtNow() {
  return new Date().toISOString();
}

/**
 * Load a source index entry's payload + manifest pair with full file-level
 * safety: regular files only, no symlinks, sha verified against the index
 * when declared.
 */
function makePairLoader(sourceIndex) {
  return async (entry) => {
    const payloadFile = String(entry.payload_file || "");
    const manifestFile = String(entry.manifest_file || "");
    const payload = readJsonFile(payloadFile);
    const manifest = readJsonFile(manifestFile);
    if (
      entry.payload_file_sha256 &&
      entry.payload_file_sha256 !== payload.sha256
    ) {
      throw Object.assign(
        new Error(`payload_file_sha256 mismatch for ${payloadFile}`),
        { code: "INPUT_ERROR" },
      );
    }
    if (
      entry.manifest_file_sha256 &&
      entry.manifest_file_sha256 !== manifest.sha256
    ) {
      throw Object.assign(
        new Error(`manifest_file_sha256 mismatch for ${manifestFile}`),
        { code: "INPUT_ERROR" },
      );
    }
    return {
      payload: payload.parsed,
      manifest: manifest.parsed,
      payloadBytes: payload.bytes,
      payloadFileSha256: payload.sha256,
    };
  };
}

/* eslint-disable-next-line complexity */
async function runBuild(args) {
  const sourceIndexPath = args["source-index"];
  const outputRoot = args["output-root"];
  const storeDir = args["store-dir"] || outputRoot;
  const runId = String(args["run-id"] || "");

  if (!sourceIndexPath || !outputRoot) {
    throw Object.assign(
      new Error("build requires --source-index and --output-root"),
      { code: "INPUT_ERROR" },
    );
  }
  const repositoryRoot = path.resolve(__dirname, "..", "..");
  verifyRepositoryExternalPath(sourceIndexPath, { repositoryRoot });
  verifyRepositoryExternalPath(outputRoot, { repositoryRoot });
  verifyRepositoryExternalPath(storeDir, { repositoryRoot });

  const { parsed: sourceIndex } = readJsonFile(sourceIndexPath);
  const indexValidation = validateSourceIndex(sourceIndex);
  if (!indexValidation.ok) {
    return {
      status: "blocked",
      code: ERROR_CODES.E001,
      message: `source index invalid: ${indexValidation.errors.join("; ")}`,
    };
  }

  const conversion = await convertAll({
    sourceIndex,
    loader: makePairLoader(sourceIndex),
  });

  const summary = commitObservations({
    results: conversion.results,
    outputRoot,
    storeDir,
    repositoryRoot,
    runId,
    builtAt: builtAtNow(),
  });

  return {
    status: "complete",
    processed_count: summary.business_projection.processed_count,
    accepted_new_count: summary.business_projection.accepted_new_count,
    accepted_repeat_exact_count:
      summary.business_projection.accepted_repeat_exact_count,
    accepted_repeat_equivalent_count:
      summary.business_projection.accepted_repeat_equivalent_count,
    rejected_count: summary.business_projection.rejected_count,
    quarantined_count: summary.business_projection.quarantined_count,
    business_projection_sha256:
      summary.business_projection.business_projection_sha256,
    output_root: outputRoot,
    store_dir: storeDir,
    run_id: runId,
    offline_only: true,
    zero_network: true,
    zero_database: true,
  };
}

async function runValidate(args) {
  const outputRoot = args["output-root"];
  const artifactPath = args.artifact;
  const storeDir = args["store-dir"] || outputRoot;
  if (!outputRoot && !artifactPath) {
    throw Object.assign(
      new Error("validate requires --output-root or --artifact"),
      { code: "INPUT_ERROR" },
    );
  }
  const repositoryRoot = path.resolve(__dirname, "..", "..");
  if (artifactPath) {
    verifyRepositoryExternalPath(artifactPath, { repositoryRoot });
    const { parsed: artifact } = readJsonFile(artifactPath);
    const validation = validateStagingArtifact(artifact);
    return {
      status: validation.ok ? "valid" : "invalid",
      artifact: artifactPath,
      ok: validation.ok,
      errors: validation.errors,
      business_hash: artifact.business_hash,
      source_match_id: artifact.source_match_id,
      import_terminal_state: artifact.import_terminal_state,
    };
  }
  verifyRepositoryExternalPath(outputRoot, { repositoryRoot });
  verifyRepositoryExternalPath(storeDir, { repositoryRoot });
  const result = validateOutputRoot(outputRoot, { storeDir, repositoryRoot });
  return {
    status: result.ok ? "valid" : "invalid",
    ok: result.ok,
    errors: result.errors,
    artifact_check_count: result.artifact_check_count,
    failed_artifact_check_count: result.failed_artifact_check_count,
    summary_present: result.summary_present,
    store_state_present: result.store_state_present,
  };
}

async function main(argv = process.argv.slice(2)) {
  const { args, positionals } = parseArgs(argv);
  if (args.help || positionals.length === 0 || positionals[0] === "help") {
    print({ usage: USAGE });
    return 0;
  }
  const subcommand = positionals[0];
  if (subcommand === "build") {
    print(await runBuild(args));
    return 0;
  }
  if (subcommand === "validate") {
    print(await runValidate(args));
    return 0;
  }
  throw new Error(`unknown subcommand: ${subcommand}`);
}

if (require.main === module) {
  main().catch((error) => {
    print({
      status: "blocked",
      code: error.code || "OPERATOR_FAILURE",
      message: error.message,
      offline_only: true,
      zero_network: true,
      zero_database: true,
    });
    process.exitCode = 1;
  });
}

module.exports = { main, parseArgs, runBuild, runValidate, USAGE };
