#!/usr/bin/env node
'use strict';

// lifecycle: permanent；GD-A01 file-first assembly entrypoint。
// 只接受显式输入与输出路径；无 DB、无网络、无 cwd/home/latest-file 自动发现。

const { GdA01ContractError, sha256Bytes } = require('../../src/infrastructure/golden_dataset/GdA01AssemblyContract');
const {
    buildAssembly,
    validateAssemblyFiles,
    writeAssemblyOutputs,
} = require('../../src/infrastructure/golden_dataset/GdA01Assembler');

const EXIT_CODES = Object.freeze({
    OK: 0,
    INPUT: 2,
    VALIDATION: 6,
    UNEXPECTED: 5,
});

function usage() {
    return [
        'GD-A01 file-first spine + historical odds assembler',
        '',
        'Build:',
        '  npm run gd:a01 -- build --spine <abs.json> --fotmob-freeze <abs.json>',
        '    --fotmob-manifest <abs.jsonl> --odds-root <abs-M3-emit-dir>',
        '    --output <abs-artifact.json> --receipt <abs-receipt.json>',
        '    --code-revision <40-hex-git-sha> [--expected-admitted <count>]',
        '',
        'Validate:',
        '  npm run gd:a01 -- validate --artifact <abs-artifact.json> --receipt <abs-receipt.json>',
        '',
        'All source inputs and outputs must be explicit repository-external paths.',
        'The command is file-first and performs no database or network access.',
    ].join('\n');
}

function readValue(argv, index, option) {
    const value = argv[index + 1];
    if (!value || value.startsWith('--')) throw new GdA01ContractError(`${option} requires a value`, 'INPUT_INVALID');
    return value;
}

function parseArgs(argv = []) {
    const command = argv[0] || 'help';
    if (command === '--help' || command === '-h' || command === 'help') return { command: 'help' };
    if (!['build', 'validate'].includes(command)) {
        throw new GdA01ContractError(`unsupported command ${command}`, 'INPUT_INVALID');
    }
    const values = {};
    const options = new Map([
        ['--spine', 'spinePath'],
        ['--fotmob-freeze', 'fotmobFreezePath'],
        ['--fotmob-manifest', 'fotmobManifestPath'],
        ['--odds-root', 'oddsRootPath'],
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
        if (!key) throw new GdA01ContractError(`unknown argument ${token}`, 'INPUT_INVALID');
        values[key] = readValue(argv, index, token);
        index += 1;
    }
    const required =
        command === 'build'
            ? [
                  'spinePath',
                  'fotmobFreezePath',
                  'fotmobManifestPath',
                  'oddsRootPath',
                  'outputPath',
                  'receiptPath',
                  'codeRevision',
              ]
            : ['artifactPath', 'receiptPath'];
    for (const field of required) {
        if (!values[field]) throw new GdA01ContractError(`${field} is required for ${command}`, 'INPUT_INVALID');
    }
    if (values.expectedAdmittedRows !== undefined) {
        values.expectedAdmittedRows = Number(values.expectedAdmittedRows);
        if (!Number.isSafeInteger(values.expectedAdmittedRows) || values.expectedAdmittedRows < 1) {
            throw new GdA01ContractError('--expected-admitted must be a positive integer', 'INPUT_INVALID');
        }
    }
    return { command, ...values };
}

function main(argv = process.argv.slice(2), dependencies = {}) {
    const stdout = dependencies.stdout || (text => process.stdout.write(text));
    const stderr = dependencies.stderr || (text => process.stderr.write(text));
    try {
        const args = parseArgs(argv);
        if (args.command === 'help') {
            stdout(`${usage()}\n`);
            return EXIT_CODES.OK;
        }
        if (args.command === 'validate') {
            const result = validateAssemblyFiles(args.artifactPath, args.receiptPath, dependencies);
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
        const result = buildAssembly(args, dependencies);
        const written = writeAssemblyOutputs(result, args, dependencies);
        stdout(
            `${JSON.stringify({
                schema_version: result.artifact.schema_version,
                admitted: result.artifact.rows.length,
                rejected: result.artifact.rejected_rows.length,
                output_business_sha256: result.artifact.business_content_sha256,
                receipt_sha256: sha256Bytes(result.receiptBytes),
                output: written.outputPath,
                receipt: written.receiptPath,
            })}\n`
        );
        return EXIT_CODES.OK;
    } catch (error) {
        const code = error instanceof GdA01ContractError ? error.code : 'UNEXPECTED_ERROR';
        stderr(`gd-a01 assembler failed: ${error.message}\n`);
        if (code === 'UNEXPECTED_ERROR') return EXIT_CODES.UNEXPECTED;
        if (code === 'ARTIFACT_HASH_MISMATCH' || code === 'BUSINESS_HASH_MISMATCH' || code === 'SCHEMA_MISMATCH') {
            return EXIT_CODES.VALIDATION;
        }
        return EXIT_CODES.INPUT;
    }
}

if (require.main === module) process.exitCode = main();

module.exports = {
    EXIT_CODES,
    main,
    parseArgs,
    usage,
};
