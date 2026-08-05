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
//     binding SHA, the archive is live-verified, and the extracted
//     payload/manifest files must hash-equal their archive members;
//   - every input path (source index, archive, receipt, payload, manifest)
//     is checked as a repository-external regular file with no symlink
//     ancestors and no overlap with the output root (FINDING_4);
//   - the store is the output root itself (single root, commit-marker
//     protocol — LOGICAL_COMMIT_MARKER, FINDING_1).

const path = require('node:path');

const {
    validateSourceIndex,
    validateStagingArtifact,
    ERROR_CODES,
} = require('../../src/infrastructure/fotmob/FotMobDetailStagingContract');
const { convertAll } = require('../../src/infrastructure/fotmob/FotMobDetailStagingConverter');
const {
    readJsonFile,
    verifyRepositoryExternalPath,
    writeJsonAtomically,
    commitObservations,
    validateOutputRoot,
} = require('../../src/infrastructure/fotmob/FotMobDetailStagingRetention');
const {
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
    '    --output-root=/absolute/external/path/out',
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
    '  Commits use the LOGICAL_COMMIT_MARKER protocol: a commit marker is the',
    '  only commit point; uncommitted residue is reported and never treated',
    '  as committed (no false physical both-or-neither claim).',
    '  Every source-index entry must be bound to exactly one verified archive',
    '  package via a package receipt (VERIFIED_PACKAGE_RECEIPT).',
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
    const receiptCache = new Map();
    const archiveCache = new Map();
    return async entry => {
        const packageId = String(entry.package || '');
        const binding = sourceIndex.archive_bindings[packageId];
        if (!binding) {
            throw Object.assign(new Error(`entry package ${packageId} has no archive binding`), {
                code: 'SAFETY_ERROR',
            });
        }
        let receipt = receiptCache.get(packageId);
        if (!receipt) {
            receipt = readJsonFile(binding.receipt, { repositoryRoot }).parsed;
            const receiptValidation = verifyPackageReceipt(receipt);
            if (!receiptValidation.ok) {
                throw Object.assign(new Error(`package receipt invalid: ${receiptValidation.errors.join('; ')}`), {
                    code: 'SAFETY_ERROR',
                });
            }
            if (String(receipt.archive_sha256 || '') !== String(binding.sha256 || '')) {
                throw Object.assign(new Error(`receipt archive sha does not match binding for package ${packageId}`), {
                    code: 'SAFETY_ERROR',
                });
            }
            if (!archiveCache.has(packageId)) {
                // Live-verify the archive once per package per run.
                archiveCache.set(packageId, verifyArchive(binding.path, binding.sha256, { repositoryRoot }));
            }
            receiptCache.set(packageId, receipt);
        }

        const loaded = verifyEntryAgainstReceipt({
            entry,
            binding,
            receipt,
            payloadFile: entry.payload_file,
            manifestFile: entry.manifest_file,
            outputRoot,
            options: { repositoryRoot },
        });

        if (entry.payload_file_sha256 && entry.payload_file_sha256 !== loaded.payloadFileSha256) {
            throw Object.assign(new Error(`payload_file_sha256 mismatch for ${entry.payload_file}`), {
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
        const { parsed: artifact } = readJsonFile(artifactPath);
        const validation = validateStagingArtifact(artifact);
        return {
            status: validation.ok ? 'valid' : 'invalid',
            artifact: artifactPath,
            ok: validation.ok,
            errors: validation.errors,
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
    const result = validateOutputRoot(outputRoot, { storeDir, repositoryRoot });
    return {
        status: result.ok ? 'valid' : 'invalid',
        ok: result.ok,
        errors: result.errors,
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
        print(await runBuild(args));
        return 0;
    }
    if (subcommand === 'validate') {
        print(await runValidate(args));
        return 0;
    }
    throw new Error(`unknown subcommand: ${subcommand}`);
}

if (require.main === module) {
    main().catch(error => {
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
