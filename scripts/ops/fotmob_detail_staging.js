#!/usr/bin/env node
'use strict';

// lifecycle: permanent
// Internal Node CLI for the offline FotMob detail staging converter /
// validator. The canonical operator surface is the Make targets
// data-fotmob-detail-staging-{help,receipt,build,validate}; this CLI is the
// engine.
//
// OFFLINE ONLY — ZERO NETWORK — ZERO DATABASE — NO MIGRATION — NO CAPTURE.
//
// The tool structurally cannot fetch (no fetcher import, no fetch/http
// usage), cannot connect to a database (no pg/ioredis import, no env DB
// variables), and ignores any NETWORK_AUTHORIZATION / DB_WRITE_AUTHORIZATION
// / capture authorization variables by design. Inputs and outputs are
// repository-external absolute paths only.
//
// PR1817 remediation:
//   - `receipt` builds a VERIFIED_PACKAGE_RECEIPT for one archive (live
//     archive SHA-256 + safe tar member inspection);
//   - `build` binds every entry to exactly one package (FINDING_3): the
//     receipt must be valid, the receipt archive SHA must equal the declared
//     binding SHA, the archive is live-verified (P0-1: per-run live
//     re-inspection with the member inventory hash, never trusting a cached
//     receipt), and the extracted payload/manifest files must hash-equal
//     their archive members;
//   - every input path (source index, archive, receipt, payload, manifest)
//     is checked as a repository-external regular file with no symlink
//     ancestors and no overlap with the output root (FINDING_4 / P1-3);
//   - inputs are read through O_NOFOLLOW fds with dev/inode identity checks
//     and outputs go to a controlled private directory under an exclusive
//     per-store lock (P1-4 TOCTOU posture — honest threat model: not a
//     defense against a same-uid sustained-race attacker);
//   - `validate` supports MODE_1_UNANCHORED (default) and
//     MODE_2_EXTERNALLY_ANCHORED via --expected-latest-marker-sha256 or a
//     repository-external --anchor-checkpoint (P1-5);
//   - the store is the output root itself (single root, commit-marker
//     protocol — LOGICAL_COMMIT_MARKER, FINDING_1).

const path = require('node:path');
const crypto = require('node:crypto');

const {
    validateSourceIndex,
    validateStagingArtifact,
    ERROR_CODES,
} = require('../../src/infrastructure/fotmob/FotMobDetailStagingContract');
const { convertAll } = require('../../src/infrastructure/fotmob/FotMobDetailStagingConverter');
const {
    readJsonFile,
    readFileSafeNoFollow,
    verifyRepositoryExternalPath,
    writeJsonAtomically,
    commitObservations,
    validateOutputRoot,
    markerFileNameForSeq,
} = require('../../src/infrastructure/fotmob/FotMobDetailStagingRetention');
const {
    verifyRepositoryExternalRegularFile,
    verifyArchive,
    inspectArchive,
    buildPackageReceipt,
    verifyPackageReceipt,
    verifyEntryAgainstReceipt,
    assertInputOutputNonOverlap,
} = require('../../src/infrastructure/fotmob/FotMobDetailStagingSourceVerification');

const USAGE = [
    'Usage:',
    '  node scripts/ops/fotmob_detail_staging.js receipt \\',
    '    --archive=/absolute/external/archive.tar.gz \\',
    '    --expected-sha256=<64-hex> \\',
    '    --package-id=<plain-identifier> \\',
    '    --payload-member=<tar member path> \\',
    '    --manifest-member=<tar member path> \\',
    '    --receipt-out=/absolute/external/receipt-<id>.json',
    '',
    '  node scripts/ops/fotmob_detail_staging.js build \\',
    '    --source-index=/absolute/external/path/source-index.json \\',
    '    --output-root=/absolute/external/path/out \\',
    '    [--run-id=<plain-identifier>]',
    '',
    '  node scripts/ops/fotmob_detail_staging.js validate \\',
    '    --output-root=/absolute/external/path/out \\',
    '    [--expected-latest-marker-sha256=<64hex> | --anchor-checkpoint=/external/checkpoint.json]',
    '',
    '  node scripts/ops/fotmob_detail_staging.js validate \\',
    '    --artifact=/absolute/external/path/observation-<id>-<hash>.artifact.json',
    '',
    '  node scripts/ops/fotmob_detail_staging.js help',
    '',
    'Safety:',
    '  OFFLINE ONLY — ZERO NETWORK — ZERO DATABASE — NO MIGRATION — NO CAPTURE',
    '  No authorization environment variable is read; fetch and DB access are',
    '  structurally impossible from this tool.',
    '  All inputs and outputs must be absolute paths OUTSIDE the repository;',
    '  regular files only; symlinks (leaf AND all ancestors) are rejected;',
    '  inputs must not overlap the output root; existing divergent outputs',
    '  fail closed.',
    '  TOCTOU posture (P1-4): inputs are read through O_NOFOLLOW fds with',
    '  dev/inode checks; outputs go to a controlled private directory via',
    '  O_EXCL tmp + same-fs rename with a pre/post directory identity check;',
    '  every commit runs under an exclusive per-store lock. These shrink the',
    '  race windows — they are NOT a defense against a same-uid attacker who',
    '  can sustain a race (honest threat model, see module headers).',
    '  Commits use the LOGICAL_COMMIT_MARKER protocol: a commit marker is the',
    '  only commit point; uncommitted residue is reported and never treated',
    '  as committed (no false physical both-or-neither claim).',
    '  Every source-index entry must be bound to exactly one verified archive',
    '  package via a package receipt (VERIFIED_PACKAGE_RECEIPT).',
    '  Anchoring (P1-5): validate WITHOUT an anchor reports integrity as',
    '  MODE_1_UNANCHORED (authenticity_status=UNANCHORED). Pass',
    '  --expected-latest-marker-sha256 or --anchor-checkpoint (a file OUTSIDE',
    '  the store) to run MODE_2_EXTERNALLY_ANCHORED: the latest commit',
    '  marker SHA is re-hashed from the store and compared to the anchor; a',
    '  mismatch fails validation. The anchor is never read from inside the',
    '  store directory.',
    '  Canonical operator entry: make data-fotmob-detail-staging-{help,receipt,build,validate}.',
].join('\n');

function parseArgs(argv) {
    const args = {};
    const positionals = [];
    for (let i = 0; i < argv.length; i += 1) {
        const token = argv[i];
        if (token === '--help' || token === '-h') {
            args.help = true;
            continue;
        }
        if (token.startsWith('--')) {
            const eq = token.indexOf('=');
            const rawKey = eq === -1 ? token.slice(2) : token.slice(2, eq);
            let value;
            if (eq !== -1) {
                value = token.slice(eq + 1);
            } else {
                const next = argv[i + 1];
                if (next !== undefined && !next.startsWith('--')) {
                    value = next;
                    i += 1;
                } else {
                    value = '';
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
 * Build a verified package receipt for one archive: live archive SHA-256
 * against the declared value, safe tar member inspection (rejects absolute
 * paths, traversal, links and special files), and a deterministic receipt
 * binding the archive SHA + member checksums root + payload/manifest member
 * names and hashes. The receipt is written atomically to a
 * repository-external path.
 */
function runReceipt(args) {
    const archive = args.archive;
    const expectedSha256 = args['expected-sha256'];
    const packageId = args['package-id'];
    const payloadMember = args['payload-member'];
    const manifestMember = args['manifest-member'];
    const receiptOut = args['receipt-out'];

    const missing = [
        'archive',
        'expected-sha256',
        'package-id',
        'payload-member',
        'manifest-member',
        'receipt-out',
    ].filter(key => !args[key]);
    if (missing.length > 0) {
        throw Object.assign(new Error(`receipt requires: ${missing.join(', ')}`), { code: 'INPUT_ERROR' });
    }
    const repositoryRoot = path.resolve(__dirname, '..', '..');
    verifyRepositoryExternalPath(archive, { repositoryRoot });
    verifyRepositoryExternalPath(receiptOut, { repositoryRoot });

    const verified = verifyArchive(archive, expectedSha256, { repositoryRoot });
    const inspected = inspectArchive(archive, { repositoryRoot });
    const receipt = buildPackageReceipt({
        packageId,
        archivePath: verified.archive_path,
        archiveSha256: verified.archive_sha256,
        members: inspected.members,
        payloadMember,
        manifestMember,
    });

    writeJsonAtomically(receiptOut, receipt, { repositoryRoot });

    return {
        status: 'complete',
        package_id: receipt.package_id,
        archive_sha256: receipt.archive_sha256,
        archive_file: receipt.archive_file,
        payload_member: receipt.payload_member,
        manifest_member: receipt.manifest_member,
        member_count: Object.keys(receipt.members).length,
        receipt_sha256: receipt.receipt_sha256,
        receipt_path: receiptOut,
        offline_only: true,
        zero_network: true,
        zero_database: true,
    };
}

/**
 * Load a source index entry's payload + manifest pair with FULL verified
 * package binding: the entry's package must exist in archive_bindings, the
 * package receipt must be valid and consistent with the binding, the archive
 * must be live-verified, and the extracted payload/manifest files must be
 * safe inputs whose SHA-256 equals the receipt's archive member hashes
 * (FINDING_3 / FINDING_4).
 */
function makePairLoader(sourceIndex, repositoryRoot, outputRoot) {
    // Per-run in-memory cache: each package's receipt DOCUMENT is read and
    // validated once per run (the receipt is a static document). The LIVE
    // archive is NEVER cached — R16-P1-1 (Codex round 16): verifyEntryAgainstReceipt
    // rejects any supplied `inspected` capability and always freshly
    // re-inspects the archive per entry, so a capability issued for an
    // archive that was later replaced at the same path can never bypass the
    // current re-verification. Nothing is ever trusted across runs — every
    // new run re-verifies the live archive from its physical bytes (P0-1: a
    // receipt can never be the sole trusted source).
    const receiptCache = new Map();
    return async entry => {
        const packageId = String(entry.package || '');
        const binding = sourceIndex.archive_bindings[packageId];
        if (!binding) {
            throw Object.assign(new Error(`entry package ${packageId} has no archive binding`), {
                code: 'SAFETY_ERROR',
            });
        }
        // R6-P3-1 (Codex round 6): the archive path itself must pass the SAME
        // input gate as every other input — repository-external regular file
        // with no symlink leaf/ancestor, and no overlap with the output root —
        // BEFORE any live archive inspection reads its bytes. Without this,
        // an archive inside the output root was only rejected late (residue
        // scan at commit time) instead of at the input gate.
        verifyRepositoryExternalRegularFile(binding.path, { repositoryRoot });
        if (outputRoot) {
            assertInputOutputNonOverlap(binding.path, outputRoot);
        }
        let receipt = receiptCache.get(packageId);
        if (!receipt) {
            // P1-3: the receipt path goes through the SAME input safety gate
            // as every other input (repository-external regular file, no
            // symlink leaf or ancestor, no overlap with the output root).
            verifyRepositoryExternalRegularFile(binding.receipt, { repositoryRoot });
            if (outputRoot) {
                assertInputOutputNonOverlap(binding.receipt, outputRoot);
            }
            receipt = readJsonFile(binding.receipt, { repositoryRoot }).parsed;
            const receiptValidation = verifyPackageReceipt(receipt);
            if (!receiptValidation.ok) {
                throw Object.assign(new Error(`package receipt invalid: ${receiptValidation.errors.join('; ')}`), {
                    code: 'SAFETY_ERROR',
                });
            }
            receiptCache.set(packageId, receipt);
        }
        // P0-1: verifyEntryAgainstReceipt always re-verifies the live
        // archive against the receipt per entry (archive SHA, full member
        // inventory and per-member hashes) — R16-P1-1: no capability cache,
        // so an archive replaced after any earlier verification is caught.
        const loaded = verifyEntryAgainstReceipt({
            entry,
            binding,
            receipt,
            payloadFile: entry.payload_file,
            manifestFile: entry.manifest_file,
            outputRoot,
            options: { repositoryRoot },
        });

        // P2-2: both declared file hashes are now REQUIRED and must equal the
        // live file SHA (which itself equals the receipt member hash and the
        // live archive member hash — enforced by verifyEntryAgainstReceipt).
        if (entry.payload_file_sha256 !== loaded.payloadFileSha256) {
            throw Object.assign(new Error(`payload_file_sha256 mismatch for ${entry.payload_file}`), {
                code: 'INPUT_ERROR',
            });
        }
        if (entry.manifest_file_sha256 !== loaded.manifestFileSha256) {
            throw Object.assign(new Error(`manifest_file_sha256 mismatch for ${entry.manifest_file}`), {
                code: 'INPUT_ERROR',
            });
        }
        return loaded;
    };
}

async function runBuild(args) {
    const sourceIndexPath = args['source-index'];
    const outputRoot = args['output-root'];
    const storeDir = args['store-dir'] || outputRoot;
    const runId = String(args['run-id'] || '');

    if (!sourceIndexPath || !outputRoot) {
        throw Object.assign(new Error('build requires --source-index and --output-root'), { code: 'INPUT_ERROR' });
    }
    const repositoryRoot = path.resolve(__dirname, '..', '..');
    verifyRepositoryExternalPath(sourceIndexPath, { repositoryRoot });
    verifyRepositoryExternalPath(outputRoot, { repositoryRoot });
    verifyRepositoryExternalPath(storeDir, { repositoryRoot });
    if (path.resolve(storeDir) !== path.resolve(outputRoot)) {
        throw Object.assign(new Error('store-dir must equal output-root (single-root commit-marker store)'), {
            code: 'INPUT_ERROR',
        });
    }
    assertInputOutputNonOverlap(sourceIndexPath, outputRoot);

    const { parsed: sourceIndex } = readJsonFile(sourceIndexPath);
    const indexValidation = validateSourceIndex(sourceIndex);
    if (!indexValidation.ok) {
        return {
            status: 'blocked',
            code: ERROR_CODES.E001,
            message: `source index invalid: ${indexValidation.errors.join('; ')}`,
        };
    }

    const conversion = await convertAll({
        sourceIndex,
        loader: makePairLoader(sourceIndex, repositoryRoot, outputRoot),
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
        status: 'complete',
        processed_count: summary.business_projection.processed_count,
        accepted_new_count: summary.business_projection.accepted_new_count,
        accepted_repeat_exact_count: summary.business_projection.accepted_repeat_exact_count,
        accepted_repeat_equivalent_count: summary.business_projection.accepted_repeat_equivalent_count,
        rejected_count: summary.business_projection.rejected_count,
        quarantined_count: summary.business_projection.quarantined_count,
        business_projection_sha256: summary.business_projection.business_projection_sha256,
        output_root: outputRoot,
        store_dir: storeDir,
        run_id: runId,
        offline_only: true,
        zero_network: true,
        zero_database: true,
    };
}

/**
 * P1-5: resolve the external anchor (if any) for MODE_2_EXTERNALLY_ANCHORED
 * validation. Two accepted sources, both OUTSIDE the store directory:
 *   - --expected-latest-marker-sha256=<64hex>  (direct operator value), or
 *   - --anchor-checkpoint=<external-json>      ({latest_marker_sha256})
 * The anchor is never read from inside the store; a checkpoint path goes
 * through the regular-file input gate and the no-follow fd read.
 *
 * @returns {string|null} 64-hex anchor, or null for MODE_1_UNANCHORED
 */
function resolveExternalAnchor(args, repositoryRoot, outputRoot) {
    const direct = String(args['expected-latest-marker-sha256'] || '');
    const checkpoint = String(args['anchor-checkpoint'] || '');
    if (direct !== '' && checkpoint !== '') {
        throw Object.assign(
            new Error('provide only one of --expected-latest-marker-sha256 or --anchor-checkpoint'),
            { code: 'INPUT_ERROR' }
        );
    }
    if (direct !== '') {
        if (!/^[0-9a-f]{64}$/.test(direct)) {
            throw Object.assign(new Error('--expected-latest-marker-sha256 must be 64 lowercase hex'), {
                code: 'INPUT_ERROR',
            });
        }
        return direct;
    }
    if (checkpoint !== '') {
        verifyRepositoryExternalPath(checkpoint, { repositoryRoot });
        verifyRepositoryExternalRegularFile(checkpoint, { repositoryRoot });
        if (outputRoot) {
            assertInputOutputNonOverlap(checkpoint, outputRoot);
        }
        const { parsed: checkpointDoc } = readJsonFile(checkpoint, { repositoryRoot });
        const anchor = String((checkpointDoc && checkpointDoc.latest_marker_sha256) || '');
        if (!/^[0-9a-f]{64}$/.test(anchor)) {
            throw Object.assign(
                new Error(`anchor checkpoint must contain latest_marker_sha256 as 64 hex: ${checkpoint}`),
                { code: 'INPUT_ERROR' }
            );
        }
        return anchor;
    }
    return null;
}

/**
 * P1-5 MODE_2: compare the store's latest commit-marker SHA — re-hashed from
 * the PHYSICAL marker file via a no-follow fd read rather than trusting the
 * validator's report alone — against the external anchor. Returns the
 * combined outcome so runValidate stays under the ESLint complexity budget.
 *
 * @param {string} outputRoot - store root
 * @param {string|null} anchor - external anchor sha256, or null for MODE_1
 * @param {object} result - validateOutputRoot result
 * @param {string} repositoryRoot - repo root (safety gates)
 * @returns {{authenticityStatus: string, ok: boolean, errors: Array}}
 */
function applyAnchorToResult(outputRoot, anchor, result, repositoryRoot) {
    const errors = [...result.errors];
    let ok = result.ok;
    if (anchor === null) {
        return { authenticityStatus: 'UNANCHORED', ok, errors };
    }
    if (!result.latest_marker_sha256) {
        return {
            authenticityStatus: 'ANCHOR_MISMATCH',
            ok: false,
            errors: [...errors, { code: 'ANCHOR_MISMATCH', message: 'anchor provided but the store has no commit marker' }],
        };
    }
    let physicalMarkerSha = null;
    try {
        const markerFile = path.join(outputRoot, markerFileNameForSeq(result.marker_count));
        physicalMarkerSha = crypto
            .createHash('sha256')
            .update(readFileSafeNoFollow(markerFile, { repositoryRoot }).bytes)
            .digest('hex');
    } catch {
        /* reported as mismatch below */
    }
    if (physicalMarkerSha !== anchor) {
        return {
            authenticityStatus: 'ANCHOR_MISMATCH',
            ok: false,
            errors: [
                ...errors,
                {
                    code: 'ANCHOR_MISMATCH',
                    message: `latest commit marker sha256 ${physicalMarkerSha || 'unreadable'} does not match external anchor ${anchor}`,
                },
            ],
        };
    }
    return { authenticityStatus: 'ANCHORED', ok, errors };
}

async function runValidate(args) {
    const outputRoot = args['output-root'];
    const artifactPath = args.artifact;
    const storeDir = args['store-dir'] || outputRoot;
    if (!outputRoot && !artifactPath) {
        throw Object.assign(new Error('validate requires --output-root or --artifact'), { code: 'INPUT_ERROR' });
    }
    const repositoryRoot = path.resolve(__dirname, '..', '..');
    if (artifactPath) {
        verifyRepositoryExternalPath(artifactPath, { repositoryRoot });
        const { parsed: artifact } = readJsonFile(artifactPath, { repositoryRoot });
        const validation = validateStagingArtifact(artifact);
        // P1-5: a single artifact has no store/commit-marker chain — the
        // integrity hash is verified, authenticity stays UNANCHORED.
        return {
            status: validation.ok ? 'valid' : 'invalid',
            artifact: artifactPath,
            ok: validation.ok,
            errors: validation.errors,
            integrity_status: validation.ok ? 'INTACT' : 'VIOLATED',
            authenticity_status: 'UNANCHORED',
            business_hash: artifact.business_hash,
            artifact_integrity_sha256: artifact.artifact_integrity_sha256,
            source_match_id: artifact.source_match_id,
            import_terminal_state: artifact.import_terminal_state,
        };
    }
    verifyRepositoryExternalPath(outputRoot, { repositoryRoot });
    verifyRepositoryExternalPath(storeDir, { repositoryRoot });
    if (path.resolve(storeDir) !== path.resolve(outputRoot)) {
        throw Object.assign(new Error('store-dir must equal output-root (single-root commit-marker store)'), {
            code: 'INPUT_ERROR',
        });
    }
    const anchor = resolveExternalAnchor(args, repositoryRoot, outputRoot);
    const result = validateOutputRoot(outputRoot, { storeDir, repositoryRoot });

    // P1-5 MODE_2: the anchor is compared against the store's latest
    // commit-marker SHA — which we RE-HASH from the physical marker file
    // (no-follow fd read) rather than trusting the validator's report alone.
    const anchored = applyAnchorToResult(outputRoot, anchor, result, repositoryRoot);
    return {
        status: anchored.ok ? 'valid' : 'invalid',
        ok: anchored.ok,
        errors: anchored.errors,
        integrity_status: result.ok ? 'INTACT' : 'VIOLATED',
        authenticity_status: anchored.authenticityStatus,
        latest_marker_sha256: result.latest_marker_sha256,
        anchor_mode: anchor === null ? 'MODE_1_UNANCHORED' : 'MODE_2_EXTERNALLY_ANCHORED',
        marker_count: result.marker_count,
        ledger_version_count: result.ledger_version_count,
        summary_count: result.summary_count,
        artifact_check_count: result.artifact_check_count,
        quarantine_check_count: result.quarantine_check_count,
        residue_files: result.residue_files,
        summary_present: result.summary_present,
        store_state_present: result.store_state_present,
    };
}

async function main(argv = process.argv.slice(2)) {
    const { args, positionals } = parseArgs(argv);
    if (args.help || positionals.length === 0 || positionals[0] === 'help') {
        print({ usage: USAGE });
        return 0;
    }
    const subcommand = positionals[0];
    if (subcommand === 'receipt') {
        print(runReceipt(args));
        return 0;
    }
    if (subcommand === 'build') {
        // R7-P1-1 (Codex round 7): a build that is explicitly refused must NOT
        // exit 0 — runBuild() returns `{status:'blocked'}` (e.g. a schema-
        // invalid source index) without throwing, and automation keying on
        // the exit code would treat the refusal as success. Only a fully
        // completed build is 0.
        const result = await runBuild(args);
        print(result);
        return result.status === 'complete' ? 0 : 1;
    }
    if (subcommand === 'validate') {
        // R6-P1-1 (Codex round 6): a validation failure must NOT exit 0 —
        // automation and CI gates key on the exit code, not the JSON report.
        // `invalid` (tampered store / anchor mismatch) and `blocked` both
        // fail closed with a non-zero code; only a fully valid store is 0.
        const result = await runValidate(args);
        print(result);
        return result.ok && result.status === 'valid' ? 0 : 1;
    }
    throw new Error(`unknown subcommand: ${subcommand}`);
}

if (require.main === module) {
    main()
        .then(code => {
            // R6-P1-1: the fulfilled return code (0 for success, non-zero for
            // a failed validate) must reach the process exit code — the old
            // wiring only handled the rejected-promise path.
            process.exitCode = code;
        })
        .catch(error => {
            print({
                status: 'blocked',
                code: error.code || 'OPERATOR_FAILURE',
                message: error.message,
                offline_only: true,
                zero_network: true,
                zero_database: true,
            });
            process.exitCode = 1;
        });
}

module.exports = { main, parseArgs, runReceipt, runBuild, runValidate, USAGE };
