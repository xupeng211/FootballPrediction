#!/usr/bin/env node
'use strict';

/* eslint-disable complexity -- one CLI makes every input, output, and safety option explicit. */

// lifecycle: permanent；canonical prematch feature-frame file-first entrypoint。
// 仅接受已经冻结且通过 GD-A03 校验的仓库外 artifact；不联网、不连 DB、不写 raw、
// 不训练、不 backtest、不预测、不激活模型。

const fs = require('node:fs');
const path = require('node:path');

const { resolveGitState } = require('../../src/infrastructure/fotmob/FotMobCandidateExporter');
const { sha256Bytes } = require('../../src/infrastructure/golden_dataset/GdA01AssemblyContract');
const { validatePriorStateOutputFiles } = require('../../src/infrastructure/golden_dataset/GdA03ArtifactContract');
const { assertNoSymlinkAncestors } = require('../../src/infrastructure/fotmob/FotMobDetailCaptureContract');
const { loadFeatureContract } = require('./gd_a03_assembler');
const {
    CanonicalPrematchFeatureFrameError,
    buildFrameOutput,
    validateFrameAgainstInputs,
    validateFrameOutputFiles,
} = require('../../src/infrastructure/golden_dataset/CanonicalPrematchFeatureFrameContract');

const EXIT_CODES = Object.freeze({ OK: 0, INPUT: 2, VALIDATION: 6, UNEXPECTED: 5 });
const FULL_GIT_SHA = /^[0-9a-f]{40}$/;

function usage() {
    return [
        'Canonical prematch training feature frame (offline, file-first)',
        '',
        'Build:',
        '  npm run feature:frame -- build --gd-a03-artifact <abs.json> --gd-a03-receipt <abs.json>',
        '    --output <abs-artifact.json> --receipt <abs-receipt.json> --code-revision <40-hex-git-sha>',
        '    [--expected-targets <count>]',
        '',
        'Validate:',
        '  npm run feature:frame -- validate --artifact <abs-artifact.json> --receipt <abs-receipt.json>',
        '    --gd-a03-artifact <abs.json> --gd-a03-receipt <abs.json> [--expected-targets <count>]',
        '',
        'Only the two explicit output files are written by build.',
    ].join('\n');
}

function fail(message, code = 'INPUT_INVALID') {
    throw new CanonicalPrematchFeatureFrameError(message, code);
}

function readValue(argv, index, option) {
    const value = argv[index + 1];
    if (!value || value.startsWith('--')) fail(`${option} requires a value`, 'INPUT_INVALID');
    return value;
}

function parseArgs(argv = []) {
    const command = argv[0] || 'help';
    if (command === 'help' || command === '--help' || command === '-h') return { command: 'help' };
    if (!['build', 'validate'].includes(command)) fail(`unsupported command ${command}`, 'INPUT_INVALID');
    const options = new Map([
        ['--gd-a03-artifact', 'gdA03ArtifactPath'],
        ['--gd-a03-receipt', 'gdA03ReceiptPath'],
        ['--output', 'outputPath'],
        ['--receipt', 'receiptPath'],
        ['--artifact', 'artifactPath'],
        ['--code-revision', 'codeRevision'],
        ['--expected-targets', 'expectedTargets'],
    ]);
    const values = {};
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
            ? ['gdA03ArtifactPath', 'gdA03ReceiptPath', 'outputPath', 'receiptPath', 'codeRevision']
            : ['artifactPath', 'receiptPath', 'gdA03ArtifactPath', 'gdA03ReceiptPath'];
    for (const field of required) if (!values[field]) fail(`${field} is required for ${command}`, 'INPUT_INVALID');
    if (command === 'build' && !FULL_GIT_SHA.test(values.codeRevision)) {
        fail('--code-revision must be a full Git SHA', 'INPUT_INVALID');
    }
    if (values.expectedTargets !== undefined) {
        values.expectedTargets = Number(values.expectedTargets);
        if (!Number.isSafeInteger(values.expectedTargets) || values.expectedTargets < 1) {
            fail('--expected-targets must be a positive integer', 'INPUT_INVALID');
        }
    }
    return { command, ...values };
}

function absolutePath(value, label) {
    if (typeof value !== 'string' || !path.isAbsolute(value)) fail(`${label} must be absolute`, 'PATH_INVALID');
    return path.resolve(value);
}

function isInsideRepository(realPath, repositoryRoot) {
    const relative = path.relative(fs.realpathSync(repositoryRoot), realPath);
    return relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative));
}

function readExternalFile(filePath, label, repositoryRoot) {
    const absolute = absolutePath(filePath, label);
    try {
        assertNoSymlinkAncestors(absolute);
    } catch (error) {
        fail(`${label} path contains a symlink: ${error.message}`, 'PATH_INVALID');
    }
    let before;
    let realPath;
    try {
        before = fs.lstatSync(absolute);
        realPath = fs.realpathSync(absolute);
    } catch {
        fail(`${label} is unavailable`, 'INPUT_MISSING');
    }
    if (!before.isFile() || before.isSymbolicLink()) fail(`${label} must be an ordinary file`, 'PATH_INVALID');
    if (isInsideRepository(realPath, repositoryRoot)) fail(`${label} must be repository-external`, 'SAFETY_BOUNDARY');
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

function readInternalFile(filePath, label, repositoryRoot) {
    const absolute = absolutePath(filePath, label);
    if (!isInsideRepository(absolute, repositoryRoot)) fail(`${label} must be inside repository`, 'SAFETY_BOUNDARY');
    let stat;
    let realPath;
    try {
        stat = fs.lstatSync(absolute);
        realPath = fs.realpathSync(absolute);
        assertNoSymlinkAncestors(absolute);
    } catch (error) {
        fail(`${label} is unavailable: ${error.message}`, 'INPUT_MISSING');
    }
    if (!stat.isFile() || stat.isSymbolicLink()) fail(`${label} must be an ordinary file`, 'PATH_INVALID');
    const bytes = fs.readFileSync(realPath);
    return { path: realPath, bytes, sha256: sha256Bytes(bytes) };
}

function outputPath(filePath, label, repositoryRoot) {
    const absolute = absolutePath(filePath, label);
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
    if (!parentStat.isDirectory() || parentStat.isSymbolicLink()) fail(`${label} parent is not ordinary`, 'PATH_INVALID');
    if (isInsideRepository(fs.realpathSync(parent), repositoryRoot)) fail(`${label} must be repository-external`, 'SAFETY_BOUNDARY');
    try {
        fs.lstatSync(absolute);
        fail(`${label} already exists`, 'OUTPUT_EXISTS');
    } catch (error) {
        if (error instanceof CanonicalPrematchFeatureFrameError) throw error;
        if (error.code !== 'ENOENT') fail(`${label} cannot be checked`, 'PATH_INVALID');
    }
    return absolute;
}

function assertRevisionMatchesHead(codeRevision, repositoryRoot) {
    let state;
    try {
        state = resolveGitState({ repositoryRoot });
    } catch (error) {
        fail(`cannot verify code revision: ${error.message}`, 'CODE_REVISION_UNVERIFIED');
    }
    if (state.revision !== codeRevision) fail(`code revision does not match HEAD ${state.revision}`, 'CODE_REVISION_MISMATCH');
}

function summary(result, output = null) {
    const { artifact } = result;
    return {
        schema_version: artifact.schema_version,
        feature_contract: artifact.feature_contract.contract_id,
        feature_contract_version: artifact.feature_contract.feature_contract_version,
        feature_count: artifact.feature_contract.training_feature_count,
        target_population: artifact.population_accounting.target_population,
        rows_accounted: artifact.population_accounting.rows_accounted,
        training_eligible: artifact.population_accounting.training_eligible,
        training_ineligible: artifact.population_accounting.training_ineligible,
        unaccounted: artifact.population_accounting.unaccounted,
        duplicate: artifact.population_accounting.duplicate,
        extra: artifact.population_accounting.extra,
        business_hash: artifact.business_content_sha256,
        feature_frame_readiness: artifact.feature_frame_readiness,
        real_training_readiness: artifact.real_training_readiness,
        output,
        validation: 'PASS',
    };
}

function build(args, repositoryRoot) {
    assertRevisionMatchesHead(args.codeRevision, repositoryRoot);
    const gdA03Artifact = readExternalFile(args.gdA03ArtifactPath, 'GD-A03 artifact', repositoryRoot);
    const gdA03Receipt = readExternalFile(args.gdA03ReceiptPath, 'GD-A03 receipt', repositoryRoot);
    const validated = validatePriorStateOutputFiles(gdA03Artifact.bytes, gdA03Receipt.bytes);
    if (args.expectedTargets !== undefined && validated.artifact.rows.length !== args.expectedTargets) {
        fail(`GD-A03 target count ${validated.artifact.rows.length} does not equal expected ${args.expectedTargets}`, 'POPULATION_MISMATCH');
    }
    const loadedContract = loadFeatureContract(repositoryRoot);
    const runtimeEngine = readInternalFile(
        path.join(repositoryRoot, 'src/ml/inference/canonical_prematch_feature_engine.py'),
        'canonical runtime semantic engine',
        repositoryRoot
    );
    const runtimeAdapter = readInternalFile(
        path.join(repositoryRoot, 'src/ml/feature_adapters/prematch.py'),
        'canonical runtime adapter',
        repositoryRoot
    );
    const result = buildFrameOutput({
        priorStateArtifact: validated.artifact,
        priorStateArtifactBytes: gdA03Artifact.bytes,
        priorStateReceipt: validated.receipt,
        priorStateReceiptBytes: gdA03Receipt.bytes,
        featureContractBinding: loadedContract,
        vNextContract: loadedContract.vNextContract,
        runtimeSemanticEngineBinding: { ...runtimeEngine, adapterSha256: runtimeAdapter.sha256 },
        codeRevision: args.codeRevision,
    });
    const artifactPath = outputPath(args.outputPath, 'frame artifact output', repositoryRoot);
    const receiptPath = outputPath(args.receiptPath, 'frame receipt output', repositoryRoot);
    if (artifactPath === receiptPath) fail('frame artifact and receipt outputs must differ', 'PATH_INVALID');
    fs.writeFileSync(artifactPath, result.artifactBytes, { flag: 'wx' });
    fs.writeFileSync(receiptPath, result.receiptBytes, { flag: 'wx' });
    return summary(result, { artifact: artifactPath, receipt: receiptPath });
}

function validate(args, repositoryRoot) {
    const artifact = readExternalFile(args.artifactPath, 'frame artifact', repositoryRoot);
    const receipt = readExternalFile(args.receiptPath, 'frame receipt', repositoryRoot);
    const result = validateFrameOutputFiles(artifact.bytes, receipt.bytes);
    assertRevisionMatchesHead(result.receipt.code_revision, repositoryRoot);
    const gdA03Artifact = readExternalFile(args.gdA03ArtifactPath, 'GD-A03 artifact', repositoryRoot);
    const gdA03Receipt = readExternalFile(args.gdA03ReceiptPath, 'GD-A03 receipt', repositoryRoot);
    const validated = validatePriorStateOutputFiles(gdA03Artifact.bytes, gdA03Receipt.bytes);
    if (args.expectedTargets !== undefined && result.artifact.rows.length !== args.expectedTargets) {
        fail(`frame target count ${result.artifact.rows.length} does not equal expected ${args.expectedTargets}`, 'POPULATION_MISMATCH');
    }
    if (args.expectedTargets !== undefined && validated.artifact.rows.length !== args.expectedTargets) {
        fail(`GD-A03 target count ${validated.artifact.rows.length} does not equal expected ${args.expectedTargets}`, 'POPULATION_MISMATCH');
    }
    const loadedContract = loadFeatureContract(repositoryRoot);
    const runtimeEngine = readInternalFile(
        path.join(repositoryRoot, 'src/ml/inference/canonical_prematch_feature_engine.py'),
        'canonical runtime semantic engine',
        repositoryRoot
    );
    const runtimeAdapter = readInternalFile(
        path.join(repositoryRoot, 'src/ml/feature_adapters/prematch.py'),
        'canonical runtime adapter',
        repositoryRoot
    );
    const bound = validateFrameAgainstInputs({
        artifactBytes: artifact.bytes,
        receiptBytes: receipt.bytes,
        priorStateArtifact: validated.artifact,
        priorStateArtifactBytes: gdA03Artifact.bytes,
        priorStateReceipt: validated.receipt,
        priorStateReceiptBytes: gdA03Receipt.bytes,
        featureContractBinding: loadedContract,
        vNextContract: loadedContract.vNextContract,
        runtimeSemanticEngineBinding: { ...runtimeEngine, adapterSha256: runtimeAdapter.sha256 },
        codeRevision: result.receipt.code_revision,
    });
    return summary(bound);
}

function main(argv = process.argv.slice(2)) {
    const repositoryRoot = path.resolve(__dirname, '../..');
    const args = parseArgs(argv);
    if (args.command === 'help') {
        process.stdout.write(`${usage()}\n`);
        return EXIT_CODES.OK;
    }
    try {
        const result = args.command === 'build' ? build(args, repositoryRoot) : validate(args, repositoryRoot);
        process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
        return EXIT_CODES.OK;
    } catch (error) {
        const code = error instanceof CanonicalPrematchFeatureFrameError ? error.code : 'UNEXPECTED';
        process.stderr.write(`${JSON.stringify({ error: error.message, code })}\n`);
        return code === 'INPUT_INVALID' || code === 'PATH_INVALID' || code === 'INPUT_MISSING' ? EXIT_CODES.INPUT : EXIT_CODES.VALIDATION;
    }
}

if (require.main === module) process.exitCode = main();

module.exports = {
    build,
    main,
    parseArgs,
    validate,
};
