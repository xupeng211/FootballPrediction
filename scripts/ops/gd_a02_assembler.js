#!/usr/bin/env node
'use strict';

// lifecycle: permanent；GD-A02 file-first facts projection entrypoint。
// 所有输入与输出均须显式指定为仓库外普通文件；不联网、不连 DB、不改 raw。

const fs = require('node:fs');
const path = require('node:path');

const {
    GdA02ContractError,
    sha256Bytes,
    validateFactsSourceIndex,
} = require('../../src/infrastructure/golden_dataset/GdA02FactsContract');
const { assertNoSymlinkAncestors } = require('../../src/infrastructure/fotmob/FotMobDetailCaptureContract');
const { buildFactsAssembly, validateFactsFiles } = require('../../src/infrastructure/golden_dataset/GdA02Assembler');

const EXIT_CODES = Object.freeze({
    OK: 0,
    INPUT: 2,
    VALIDATION: 6,
    UNEXPECTED: 5,
});
const GIT_REVISION = /^[0-9a-f]{40}$/;

function usage() {
    return [
        'GD-A02 file-first FotMob facts assembler',
        '',
        'Build:',
        '  npm run gd:a02 -- build --gd-a01-artifact <abs.json> --gd-a01-receipt <abs.json>',
        '    --fotmob-freeze <abs.json> --fotmob-manifest <abs.jsonl>',
        '    --facts-source-index <abs.json> --output <abs-artifact.json>',
        '    --receipt <abs-receipt.json> --code-revision <40-hex-git-sha>',
        '    [--expected-admitted <count>]',
        '',
        'Validate:',
        '  npm run gd:a02 -- validate --artifact <abs-artifact.json>',
        '    --receipt <abs-receipt.json> [--expected-admitted <count>]',
        '',
        'The command is file-first, offline, and writes only the two explicit output files.',
    ].join('\n');
}

function fail(message, code = 'GD_A02_INPUT_INVALID') {
    throw new GdA02ContractError(message, code);
}

function readValue(argv, index, option) {
    const value = argv[index + 1];
    if (!value || value.startsWith('--')) fail(`${option} requires a value`, 'INPUT_INVALID');
    return value;
}

// eslint-disable-next-line complexity
function parseArgs(argv = []) {
    const command = argv[0] || 'help';
    if (command === '--help' || command === '-h' || command === 'help') return { command: 'help' };
    if (!['build', 'validate'].includes(command)) fail(`unsupported command ${command}`, 'INPUT_INVALID');
    const values = {};
    const options = new Map([
        ['--gd-a01-artifact', 'gdA01ArtifactPath'],
        ['--gd-a01-receipt', 'gdA01ReceiptPath'],
        ['--fotmob-freeze', 'fotmobFreezePath'],
        ['--fotmob-manifest', 'fotmobManifestPath'],
        ['--facts-source-index', 'factsSourceIndexPath'],
        ['--output', 'outputPath'],
        ['--receipt', 'receiptPath'],
        ['--artifact', 'artifactPath'],
        ['--code-revision', 'codeRevision'],
        ['--expected-admitted', 'expectedAdmittedRows'],
    ]);
    for (let index = 1; index < argv.length; index += 1) {
        const token = argv[index];
        const equalOption = [...options.keys()].find(option => token.startsWith(`${option}=`));
        if (equalOption) {
            values[options.get(equalOption)] = token.slice(equalOption.length + 1);
            continue;
        }
        const key = options.get(token);
        if (!key) fail(`unknown argument ${token}`, 'INPUT_INVALID');
        values[key] = readValue(argv, index, token);
        index += 1;
    }
    const required =
        command === 'build'
            ? [
                  'gdA01ArtifactPath',
                  'gdA01ReceiptPath',
                  'fotmobFreezePath',
                  'fotmobManifestPath',
                  'factsSourceIndexPath',
                  'outputPath',
                  'receiptPath',
                  'codeRevision',
              ]
            : ['artifactPath', 'receiptPath'];
    for (const field of required) {
        if (!values[field]) fail(`${field} is required for ${command}`, 'INPUT_INVALID');
    }
    if (command === 'build' && !GIT_REVISION.test(values.codeRevision)) {
        fail('--code-revision must be a full Git SHA', 'INPUT_INVALID');
    }
    if (values.expectedAdmittedRows !== undefined) {
        values.expectedAdmittedRows = Number(values.expectedAdmittedRows);
        if (!Number.isSafeInteger(values.expectedAdmittedRows) || values.expectedAdmittedRows < 1) {
            fail('--expected-admitted must be a positive integer', 'INPUT_INVALID');
        }
    }
    return { command, ...values };
}

function resolvedPath(value, label) {
    if (typeof value !== 'string' || !path.isAbsolute(value)) fail(`${label} must be absolute`, 'PATH_INVALID');
    return path.resolve(value);
}

function assertExternalRegularFile(filePath, label, repositoryRoot) {
    const absolute = resolvedPath(filePath, label);
    try {
        assertNoSymlinkAncestors(absolute);
    } catch (error) {
        fail(`${label} path contains a symlink: ${error.message}`, 'PATH_INVALID');
    }
    let stat;
    let realPath;
    try {
        stat = fs.lstatSync(absolute);
        realPath = fs.realpathSync(absolute);
    } catch {
        fail(`${label} is unavailable`, 'INPUT_MISSING');
    }
    if (!stat.isFile() || stat.isSymbolicLink()) fail(`${label} must be an ordinary file`, 'PATH_INVALID');
    const repository = fs.realpathSync(repositoryRoot);
    const relative = path.relative(repository, realPath);
    if (relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative))) {
        fail(`${label} must be repository-external`, 'SAFETY_BOUNDARY');
    }
    const before = fs.lstatSync(realPath);
    const bytes = fs.readFileSync(realPath);
    const after = fs.lstatSync(realPath);
    if (
        before.dev !== after.dev ||
        before.ino !== after.ino ||
        before.size !== after.size ||
        before.mtimeMs !== after.mtimeMs
    ) {
        fail(`${label} changed while being read`, 'INPUT_MUTATED');
    }
    return { path: realPath, bytes, sha256: sha256Bytes(bytes) };
}

function parseJson(binding, label) {
    try {
        return JSON.parse(binding.bytes.toString('utf8'));
    } catch (error) {
        fail(`${label} is not valid JSON: ${error.message}`, 'SCHEMA_MISMATCH');
    }
}

function parseJsonLines(binding, label) {
    const lines = binding.bytes.toString('utf8').split('\n');
    if (lines.at(-1) === '') lines.pop();
    return lines.map((line, index) => {
        if (!line.trim()) fail(`${label} contains a blank line at ${index + 1}`, 'SCHEMA_MISMATCH');
        try {
            return JSON.parse(line);
        } catch (error) {
            fail(`${label} contains invalid JSON at line ${index + 1}: ${error.message}`, 'SCHEMA_MISMATCH');
        }
    });
}

function assertOutputPath(filePath, label, repositoryRoot) {
    const absolute = resolvedPath(filePath, label);
    try {
        assertNoSymlinkAncestors(absolute);
    } catch (error) {
        fail(`${label} path contains a symlink: ${error.message}`, 'PATH_INVALID');
    }
    const parent = path.dirname(absolute);
    let parentStat;
    try {
        parentStat = fs.lstatSync(parent);
    } catch {
        fail(`${label} parent is unavailable`, 'PATH_INVALID');
    }
    if (!parentStat.isDirectory() || parentStat.isSymbolicLink()) {
        fail(`${label} parent is not an ordinary directory`, 'PATH_INVALID');
    }
    const repository = fs.realpathSync(repositoryRoot);
    const realParent = fs.realpathSync(parent);
    const relative = path.relative(repository, realParent);
    if (relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative))) {
        fail(`${label} must be repository-external`, 'SAFETY_BOUNDARY');
    }
    try {
        fs.lstatSync(absolute);
        fail(`${label} already exists`, 'OUTPUT_EXISTS');
    } catch (error) {
        if (error instanceof GdA02ContractError) throw error;
        if (error.code !== 'ENOENT') fail(`${label} cannot be checked`, 'PATH_INVALID');
    }
    return absolute;
}

function loadSourcePairs(sourceIndex, repositoryRoot) {
    const entries = validateFactsSourceIndex(sourceIndex);
    const pairs = new Map();
    for (const entry of entries) {
        const staging = assertExternalRegularFile(
            entry.staging_artifact_path,
            `${entry.canonical_match_id} staging artifact`,
            repositoryRoot
        );
        const payload = assertExternalRegularFile(
            entry.capture_payload_path,
            `${entry.canonical_match_id} capture payload`,
            repositoryRoot
        );
        const manifest = assertExternalRegularFile(
            entry.capture_manifest_path,
            `${entry.canonical_match_id} capture manifest`,
            repositoryRoot
        );
        pairs.set(entry.canonical_match_id, {
            stagingArtifactBytes: staging.bytes,
            stagingArtifact: parseJson(staging, `${entry.canonical_match_id} staging artifact`),
            capturePayloadBytes: payload.bytes,
            capturePayload: parseJson(payload, `${entry.canonical_match_id} capture payload`),
            captureManifestBytes: manifest.bytes,
            captureManifest: parseJson(manifest, `${entry.canonical_match_id} capture manifest`),
        });
    }
    return pairs;
}

function loadBuildInputs(args, repositoryRoot) {
    const gdA01Artifact = assertExternalRegularFile(args.gdA01ArtifactPath, 'GD-A01 artifact', repositoryRoot);
    const gdA01Receipt = assertExternalRegularFile(args.gdA01ReceiptPath, 'GD-A01 receipt', repositoryRoot);
    const freeze = assertExternalRegularFile(args.fotmobFreezePath, 'FotMob freeze', repositoryRoot);
    const manifest = assertExternalRegularFile(args.fotmobManifestPath, 'FotMob manifest', repositoryRoot);
    const sourceIndex = assertExternalRegularFile(
        args.factsSourceIndexPath,
        'GD-A02 facts source index',
        repositoryRoot
    );
    const sourceIndexDocument = parseJson(sourceIndex, 'GD-A02 facts source index');
    return {
        gdA01ArtifactBytes: gdA01Artifact.bytes,
        gdA01ReceiptBytes: gdA01Receipt.bytes,
        fotmobFreezeBytes: freeze.bytes,
        fotmobFreezeSha256: freeze.sha256,
        fotmobFreezeDocument: parseJson(freeze, 'FotMob freeze'),
        fotmobManifestBytes: manifest.bytes,
        fotmobManifestRows: parseJsonLines(manifest, 'FotMob manifest'),
        factsSourceIndex: sourceIndexDocument,
        factsSourceIndexBytes: sourceIndex.bytes,
        factsSourceIndexSha256: sourceIndex.sha256,
        loadedFactsByCanonicalId: loadSourcePairs(sourceIndexDocument, repositoryRoot),
        codeRevision: args.codeRevision,
    };
}

function writeOutputs(result, args, repositoryRoot) {
    const outputPath = assertOutputPath(args.outputPath, 'GD-A02 artifact output', repositoryRoot);
    const receiptPath = assertOutputPath(args.receiptPath, 'GD-A02 receipt output', repositoryRoot);
    if (outputPath === receiptPath) fail('GD-A02 artifact and receipt outputs must differ', 'PATH_INVALID');
    fs.writeFileSync(outputPath, result.artifactBytes, { flag: 'wx' });
    fs.writeFileSync(receiptPath, result.receiptBytes, { flag: 'wx' });
    return { outputPath, receiptPath };
}

function main(argv = process.argv.slice(2), dependencies = {}) {
    const stdout = dependencies.stdout || (text => process.stdout.write(text));
    const stderr = dependencies.stderr || (text => process.stderr.write(text));
    const repositoryRoot = dependencies.repositoryRoot || path.resolve(__dirname, '../..');
    try {
        const args = parseArgs(argv);
        if (args.command === 'help') {
            stdout(`${usage()}\n`);
            return EXIT_CODES.OK;
        }
        if (args.command === 'validate') {
            const artifact = assertExternalRegularFile(args.artifactPath, 'GD-A02 artifact', repositoryRoot);
            const receipt = assertExternalRegularFile(args.receiptPath, 'GD-A02 receipt', repositoryRoot);
            const result = validateFactsFiles(artifact.bytes, receipt.bytes, {
                expectedAdmittedRows: args.expectedAdmittedRows,
            });
            stdout(
                `${JSON.stringify({
                    schema_version: result.artifact.schema_version,
                    admitted: result.artifact.rows.length,
                    rejected: result.artifact.rejected_rows.length,
                    output_business_sha256: result.artifact.business_content_sha256,
                    validation: 'PASS',
                })}\n`
            );
            return EXIT_CODES.OK;
        }
        const result = buildFactsAssembly(loadBuildInputs(args, repositoryRoot));
        validateFactsFiles(result.artifactBytes, result.receiptBytes, {
            expectedAdmittedRows: args.expectedAdmittedRows,
        });
        const written = writeOutputs(result, args, repositoryRoot);
        stdout(
            `${JSON.stringify({
                schema_version: result.artifact.schema_version,
                admitted: result.artifact.rows.length,
                rejected: result.artifact.rejected_rows.length,
                accounted: result.artifact.rows.length + result.artifact.rejected_rows.length,
                output_business_sha256: result.artifact.business_content_sha256,
                status: result.receipt.status,
                output: written.outputPath,
                receipt: written.receiptPath,
            })}\n`
        );
        return result.receipt.status === 'COMPLETE' ? EXIT_CODES.OK : EXIT_CODES.VALIDATION;
    } catch (error) {
        const code =
            error instanceof GdA02ContractError || typeof error?.code === 'string' ? error.code : 'UNEXPECTED_ERROR';
        stderr(`gd-a02 assembler failed: ${error.message}\n`);
        if (code === 'UNEXPECTED_ERROR') return EXIT_CODES.UNEXPECTED;
        if (
            [
                'ARTIFACT_HASH_MISMATCH',
                'BUSINESS_HASH_MISMATCH',
                'SCHEMA_MISMATCH',
                'POPULATION_MISMATCH',
                'DETERMINISM_FAILURE',
            ].includes(code)
        ) {
            return EXIT_CODES.VALIDATION;
        }
        return EXIT_CODES.INPUT;
    }
}

if (require.main === module) process.exitCode = main();

module.exports = {
    EXIT_CODES,
    loadSourcePairs,
    main,
    parseArgs,
    usage,
};
